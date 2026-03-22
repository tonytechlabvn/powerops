"""AI Template Studio routes.

POST /api/ai/studio/generate    — NL → template package
POST /api/ai/studio/extract     — HCL → template package
POST /api/ai/studio/refine      — iterative refinement
POST /api/ai/studio/validate    — validate template files
POST /api/ai/studio/save        — persist template to disk
GET  /api/ai/studio/load/{name} — load studio-created template
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/ai/studio", tags=["ai-studio"])


# ---------------------------------------------------------------------------
# Module loaders (lazy, avoids circular imports)
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
    return _load("schemas/ai-studio-schemas.py", "api.schemas.ai_studio_schemas")


def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _get_studio():
    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    studio_mod = load_kebab_module("ai-template-studio.py", "ai_template_studio")
    return studio_mod.AITemplateStudio(config=get_settings())


def _template_to_response(template, validation, schemas):
    """Convert GeneratedTemplate + validation into a TemplateFileResponse."""
    val_resp = None
    if validation is not None:
        val_resp = schemas.TemplateValidationResponse(
            valid=validation.valid,
            jinja2_errors=validation.jinja2_errors,
            hcl_errors=validation.hcl_errors,
            structure_warnings=validation.structure_warnings,
        )
    return schemas.TemplateFileResponse(
        name=template.name,
        providers=template.providers,
        description=template.description,
        display_name=template.display_name,
        files=template.files,
        tags=template.tags,
        version=template.version,
        validation=val_resp,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_template(request: Request):
    """Generate a Jinja2 template package from a natural language description."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.GenerateTemplateRequest(**(await request.json()))

    studio = _get_studio()
    template = await studio.generate_template(
        description=body.description,
        providers=body.providers,
        complexity=body.complexity,
        additional_context=body.additional_context,
    )
    validation = await studio.validate_template(template)
    return _template_to_response(template, validation, schemas)


@router.post("/extract")
async def extract_template(request: Request):
    """Extract a Jinja2 template from raw HCL code."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.ExtractTemplateRequest(**(await request.json()))

    studio = _get_studio()
    template = await studio.extract_template(
        hcl_code=body.hcl_code,
        template_name=body.template_name,
    )
    validation = await studio.validate_template(template)
    return _template_to_response(template, validation, schemas)


@router.post("/refine")
async def refine_template(request: Request):
    """Refine a template with conversational instructions."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.RefineTemplateRequest(**(await request.json()))

    from backend.core import load_kebab_module
    helpers = load_kebab_module("ai-template-studio-helpers.py", "ai_template_studio_helpers")

    current = helpers.GeneratedTemplate(
        name=body.template_name,
        providers=body.providers,
        description=body.description,
        files=body.template_files,
    )

    studio = _get_studio()
    refined = await studio.refine_template(
        current_template=current,
        refinement=body.refinement,
        conversation_history=body.conversation_history,
    )
    validation = await studio.validate_template(refined)
    return _template_to_response(refined, validation, schemas)


@router.post("/validate")
async def validate_template(request: Request):
    """Validate template files for Jinja2 syntax and HCL correctness."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.ValidateTemplateRequest(**(await request.json()))

    from backend.core import load_kebab_module
    helpers = load_kebab_module("ai-template-studio-helpers.py", "ai_template_studio_helpers")

    template = helpers.GeneratedTemplate(
        name="", providers=[], description="", files=body.template_files,
    )

    studio = _get_studio()
    validation = await studio.validate_template(template)

    return schemas.TemplateValidationResponse(
        valid=validation.valid,
        jinja2_errors=validation.jinja2_errors,
        hcl_errors=validation.hcl_errors,
        structure_warnings=validation.structure_warnings,
    )


@router.post("/save")
async def save_template(request: Request):
    """Persist a template package to the template library on disk."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.SaveTemplateRequest(**(await request.json()))

    from backend.core import load_kebab_module
    helpers = load_kebab_module("ai-template-studio-helpers.py", "ai_template_studio_helpers")

    template = helpers.GeneratedTemplate(
        name=body.template_name,
        providers=body.providers,
        description=body.description,
        files=body.files,
        display_name=body.display_name,
        tags=body.tags,
    )

    studio = _get_studio()
    try:
        saved_path = studio.save_template(template, overwrite=body.overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return schemas.SaveTemplateResponse(
        saved_path=saved_path,
        message=f"Template saved to {saved_path}",
    )


@router.post("/wizard-steps")
async def wizard_steps(request: Request):
    """Analyze description and return applicable wizard steps with AI-populated defaults."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.WizardStepsRequest(**(await request.json()))

    studio = _get_studio()
    result = await studio.analyze_wizard_steps(body.description)

    return schemas.WizardStepsResponse(
        steps=result.get("steps", []),
        defaults=result.get("defaults", {}),
        reasoning=result.get("reasoning", ""),
    )


@router.get("/load/{name:path}")
async def load_template(name: str, request: Request):
    """Load a studio-created template for re-editing."""
    _require_auth(request)
    schemas = _schemas()

    studio = _get_studio()
    template = studio.load_template(name)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")

    return _template_to_response(template, None, schemas)
