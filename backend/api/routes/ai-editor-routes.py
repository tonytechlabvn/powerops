"""AI editor routes — streaming SSE endpoints for inline HCL assistance (Phase 8).

POST /api/workspaces/{workspace_id}/ai/generate  — stream-generate HCL (SSE)
POST /api/workspaces/{workspace_id}/ai/explain   — stream-explain code (SSE)
POST /api/workspaces/{workspace_id}/ai/fix       — stream-suggest fix (SSE)
POST /api/workspaces/{workspace_id}/ai/complete  — inline completion (JSON)
POST /api/workspaces/{workspace_id}/ai/chat      — stream chat (SSE)
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/workspaces", tags=["ai-editor"])


# ---------------------------------------------------------------------------
# Lazy module loaders (kebab-case pattern from project conventions)
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
    return _load("schemas/ai-editor-schemas.py", "api.schemas.ai_editor_schemas")


def _settings():
    from backend.core.config import get_settings
    return get_settings()


def _workspace_path(workspace_id: str) -> _P:
    from backend.core.config import get_settings
    settings = get_settings()
    base = _P(settings.working_dir).resolve()
    ws = (base / workspace_id).resolve()
    if not str(ws).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid workspace path")
    return ws


def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _sse_response(generator) -> StreamingResponse:
    """Wrap an async generator as an SSE StreamingResponse."""
    async def event_stream():
        async for chunk in generator:
            # Each chunk is a text delta; encode as SSE data line
            safe = chunk.replace("\n", " ")
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{workspace_id}/ai/generate")
async def ai_generate(workspace_id: str, request: Request):
    """Stream-generate HCL from a natural language prompt."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.GenerateRequest(**(await request.json()))

    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    assistant_mod = load_kebab_module("ai-code-assistant.py", "ai_code_assistant")
    assistant = assistant_mod.AICodeAssistant(
        config=get_settings(),
        workspace_dir=_workspace_path(workspace_id),
    )
    gen = assistant.generate_code(
        prompt=body.prompt,
        current_file=body.current_file,
        current_content=body.current_content,
        provider=body.provider,
    )
    return _sse_response(gen)


@router.post("/{workspace_id}/ai/explain")
async def ai_explain(workspace_id: str, request: Request):
    """Stream a plain-English explanation of a selected HCL block."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.ExplainRequest(**(await request.json()))

    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    assistant_mod = load_kebab_module("ai-code-assistant.py", "ai_code_assistant")
    assistant = assistant_mod.AICodeAssistant(config=get_settings())
    gen = assistant.explain_code(code=body.code, file_path=body.file_path)
    return _sse_response(gen)


@router.post("/{workspace_id}/ai/fix")
async def ai_fix(workspace_id: str, request: Request):
    """Stream a suggested HCL fix for a validation or plan error."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.FixRequest(**(await request.json()))

    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    assistant_mod = load_kebab_module("ai-code-assistant.py", "ai_code_assistant")
    assistant = assistant_mod.AICodeAssistant(config=get_settings())
    gen = assistant.suggest_fix(code=body.code, error=body.error, file_path=body.file_path)
    return _sse_response(gen)


@router.post("/{workspace_id}/ai/complete")
async def ai_complete(workspace_id: str, request: Request):
    """Return an inline completion suggestion (JSON, non-streaming)."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.CompleteRequest(**(await request.json()))

    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    assistant_mod = load_kebab_module("ai-code-assistant.py", "ai_code_assistant")
    assistant = assistant_mod.AICodeAssistant(config=get_settings())
    suggestion = await assistant.complete_code(
        code=body.code,
        cursor_line=body.cursor_line,
        cursor_col=body.cursor_col,
        file_path=body.file_path,
    )
    return schemas.CompletionResponse(suggestion=suggestion, confidence=0.8)


@router.post("/{workspace_id}/ai/chat")
async def ai_chat(workspace_id: str, request: Request):
    """Stream a conversational response with workspace file context."""
    _require_auth(request)
    schemas = _schemas()
    body = schemas.ChatRequest(**(await request.json()))

    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    assistant_mod = load_kebab_module("ai-code-assistant.py", "ai_code_assistant")
    assistant = assistant_mod.AICodeAssistant(
        config=get_settings(),
        workspace_dir=_workspace_path(workspace_id),
    )
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    gen = assistant.chat(
        messages=messages,
        current_file=body.current_file,
        current_content=body.current_content,
    )
    return _sse_response(gen)
