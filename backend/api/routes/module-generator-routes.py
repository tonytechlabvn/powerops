"""AI module generator routes (Phase 11).

POST /api/ai/generate-module           — generate module from NL description (SSE stream)
POST /api/ai/generate-module/refine    — refine previously generated module (SSE)
POST /api/ai/generate-module/validate  — validate generated module files (JSON)
POST /api/ai/generate-module/publish   — validate + publish to registry (JSON)
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/ai", tags=["module-generator"])


# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

def _load(rel: str, alias: str):
    full = f"backend.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    base = _P(__file__).resolve().parent.parent
    spec = _ilu.spec_from_file_location(full, base / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _schemas():
    return _load("schemas/module-generator-schemas.py", "api.schemas.module_generator_schemas")


def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _get_generator():
    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    from backend.core.llm import get_llm_client
    gen_mod = load_kebab_module("ai-module-generator.py", "ai_module_generator")
    cfg = get_settings()
    return gen_mod.AIModuleGenerator(client=get_llm_client(cfg), max_tokens=cfg.ai_max_tokens)


def _module_to_response(module, validation, schemas):
    val_resp = None
    if validation is not None:
        val_resp = schemas.ModuleValidationResponse(
            valid=validation.valid,
            file_errors=validation.file_errors,
            structure_warnings=validation.structure_warnings,
        )
    return schemas.GeneratedModuleResponse(
        name=module.name,
        provider=module.provider,
        description=module.description,
        files=module.files,
        resources=module.resources,
        validation=val_resp,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate-module")
async def generate_module(request: Request):
    """Generate a complete Terraform module from a natural language description.

    Returns GeneratedModuleResponse with all module files and validation result.
    Non-streaming variant — waits for full generation then validates.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.GenerateModuleRequest(**(await request.json()))

    generator = _get_generator()
    module = await generator.generate_module(
        description=body.description,
        provider=body.provider,
        complexity=body.complexity,
        additional_context=body.additional_context,
    )
    validation = await generator.validate_module(module)
    return _module_to_response(module, validation, schemas)


@router.post("/generate-module/stream")
async def generate_module_streaming(request: Request):
    """Stream module generation progress as SSE events.

    Yields raw text deltas as they arrive from Claude, then a final [DONE] event.
    Client should call /generate-module (non-streaming) or /validate after to get structured result.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.GenerateModuleRequest(**(await request.json()))

    generator = _get_generator()

    async def event_stream():
        async for event in generator.generate_module_streaming(
            description=body.description,
            provider=body.provider,
            complexity=body.complexity,
        ):
            if event.type == "file_content" and event.content:
                safe = event.content.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
            elif event.type == "file_complete" and event.file_name:
                yield f"event: file_complete\ndata: {event.file_name}\n\n"
            elif event.type == "done":
                yield "data: [DONE]\n\n"
            elif event.type == "error":
                yield f"event: error\ndata: {event.content}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/generate-module/refine")
async def refine_module(request: Request):
    """Refine a previously generated module with additional instructions.

    Accepts current module files and a refinement instruction.
    Returns updated module with re-validation.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.RefineModuleRequest(**(await request.json()))

    from backend.core import load_kebab_module
    helpers_mod = load_kebab_module("ai-module-generator-helpers.py", "ai_module_generator_helpers")

    current = helpers_mod.GeneratedModule(
        name=body.name,
        provider=body.provider,
        description=body.description,
        files=body.module_files,
    )

    generator = _get_generator()
    refined = await generator.refine_module(current_module=current, refinement=body.refinement)
    validation = await generator.validate_module(refined)
    return _module_to_response(refined, validation, schemas)


@router.post("/generate-module/validate")
async def validate_module(request: Request):
    """Validate generated module files for HCL syntax and structure completeness."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.ValidateModuleRequest(**(await request.json()))

    from backend.core import load_kebab_module
    helpers_mod = load_kebab_module("ai-module-generator-helpers.py", "ai_module_generator_helpers")
    module = helpers_mod.GeneratedModule(
        name="", provider="", description="", files=body.module_files
    )

    generator = _get_generator()
    validation = await generator.validate_module(module)

    return schemas.ModuleValidationResponse(
        valid=validation.valid,
        file_errors=validation.file_errors,
        structure_warnings=validation.structure_warnings,
    )
