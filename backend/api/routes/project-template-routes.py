"""Project template and AI wizard endpoints.

GET  /api/project-templates              — list templates (filter: category, provider)
GET  /api/project-templates/{name}       — full template detail
POST /api/project-templates/{name}/create — create project from template
POST /api/project-wizard/message         — wizard chat turn
POST /api/project-wizard/confirm         — create project from wizard-generated YAML
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import re
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Kebab-case module loaders
# ---------------------------------------------------------------------------

def _load_schema(rel: str, alias: str):
    full = f"backend.api.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_core(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent.parent / "core" / rel
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_schemas = _load_schema("schemas/project-template-schemas.py", "schemas.project_template_schemas")

router = APIRouter(tags=["project-templates"])


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_auth(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if state is None or not isinstance(state, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------

@router.get("/api/project-templates", response_model=list[_schemas.TemplateResponse])
async def list_templates(
    category: str | None = None,
    provider: str | None = None,
):
    """List all available project templates with optional category/provider filters."""
    engine = _load_core("project-template-engine.py", "project_template_engine")
    templates = engine.list_project_templates(category=category, provider=provider)
    return [_schemas.TemplateResponse(**t) for t in templates]


@router.get("/api/project-templates/{name}", response_model=_schemas.TemplateDetailResponse)
async def get_template(name: str):
    """Return full detail for a single template including variables and modules."""
    engine = _load_core("project-template-engine.py", "project_template_engine")
    data = engine.get_project_template(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return _schemas.TemplateDetailResponse(
        name=data["name"],
        display_name=data.get("display_name", data["name"]),
        description=data.get("description", ""),
        category=data.get("category", ""),
        complexity=data.get("complexity", ""),
        providers=data.get("providers", []),
        tags=data.get("tags", []),
        variables=[_schemas.TemplateVariableSchema(**v) for v in data.get("variables", [])],
        modules=[_schemas.TemplateModuleSchema(**m) for m in data.get("modules", [])],
        roles=data.get("roles", []),
        outputs=[_schemas.TemplateOutputSchema(**o) for o in data.get("outputs", [])],
    )


@router.post(
    "/api/project-templates/{name}/create",
    response_model=_schemas.CreateFromTemplateResponse,
    status_code=201,
)
async def create_project_from_template(
    name: str,
    body: _schemas.CreateFromTemplateRequest,
    request: Request,
):
    """Create a new project (with modules) from the named template."""
    user = _require_auth(request)
    engine = _load_core("project-template-engine.py", "project_template_engine")

    try:
        project_id = await engine.create_project_from_template(
            template_name=name,
            project_name=body.project_name,
            variables=body.variables,
            user_id=user["user_id"],
            org_id=user.get("org_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Error creating project from template %r: %s", name, exc)
        raise HTTPException(status_code=500, detail="Failed to create project from template")

    resolved_name = body.project_name.strip() or name
    return _schemas.CreateFromTemplateResponse(
        project_id=project_id,
        project_name=resolved_name,
        template_name=name,
    )


# ---------------------------------------------------------------------------
# Wizard endpoints
# ---------------------------------------------------------------------------

def _extract_yaml_block(text: str) -> str | None:
    """Extract content from the first ```yaml fenced block in text."""
    match = re.search(r"```yaml\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


@router.post("/api/project-wizard/message", response_model=_schemas.WizardMessageResponse)
async def wizard_message(body: _schemas.WizardMessageRequest, request: Request):
    """Send a message to the AI project wizard. Returns assistant response + optional YAML."""
    _require_auth(request)

    from backend.core.config import get_settings
    _ai_mod = _load_core("ai-agent.py", "ai_agent")
    _wizard_prompt = _load_core("prompts/project-wizard-prompt.py", "prompts.project_wizard_prompt")

    settings = get_settings()
    agent = _ai_mod.AIAgent(config=settings)

    # Build message list: history + new user message
    messages = [{"role": m.role, "content": m.content} for m in body.history]
    messages.append({"role": "user", "content": body.message})

    # Collect full response (non-streaming for wizard — we need the full text to extract YAML)
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens,
            system=_wizard_prompt.get_prompt(),
            messages=messages,  # type: ignore[arg-type]
        )
        full_text: str = response.content[0].text if response.content else ""
    except Exception as exc:
        logger.error("Wizard message error: %s", exc)
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")

    project_yaml = _extract_yaml_block(full_text)

    return _schemas.WizardMessageResponse(
        response=full_text,
        project_yaml=project_yaml,
    )


@router.post(
    "/api/project-wizard/confirm",
    response_model=_schemas.CreateFromTemplateResponse,
    status_code=201,
)
async def wizard_confirm(body: _schemas.WizardConfirmRequest, request: Request):
    """Create a project from a wizard-generated YAML string."""
    user = _require_auth(request)

    import yaml as _yaml

    try:
        data = _yaml.safe_load(body.project_yaml)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}")

    if not isinstance(data, dict) or "name" not in data:
        raise HTTPException(status_code=400, detail="YAML must be a mapping with a 'name' field")

    from backend.db.database import get_session
    from backend.db.models import Project, ProjectMember, ProjectModule

    resolved_name = body.project_name.strip() or data.get("name", "wizard-project")

    try:
        async with get_session() as session:
            project = Project(
                name=resolved_name,
                description=data.get("description", ""),
                config_yaml=body.project_yaml,
                org_id=user.get("org_id"),
                created_by=user["user_id"],
            )
            session.add(project)
            await session.flush()

            for m in data.get("modules", []):
                if not isinstance(m, dict) or "name" not in m:
                    continue
                provider = m.get("provider", "")
                session.add(ProjectModule(
                    project_id=project.id,
                    name=m["name"],
                    path=f"modules/{provider}/{m['name']}" if provider else f"modules/{m['name']}",
                    provider=provider,
                    depends_on=m.get("depends_on", []),
                ))

            session.add(ProjectMember(
                project_id=project.id,
                user_id=user["user_id"],
                role_name="workspace-admin",
            ))
            await session.flush()
            project_id: str = project.id

    except Exception as exc:
        logger.exception("Wizard confirm error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create project from wizard YAML")

    return _schemas.CreateFromTemplateResponse(
        project_id=project_id,
        project_name=resolved_name,
        template_name="ai-wizard",
    )
