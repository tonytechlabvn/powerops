"""Stack Composition & Template API routes.

POST   /api/stacks/compose                  — compose project from module selection
GET    /api/stack-templates                 — list stack templates
POST   /api/stack-templates                 — save stack template
GET    /api/stack-templates/{id}            — get stack template detail
PATCH  /api/stack-templates/{id}            — update stack template
DELETE /api/stack-templates/{id}            — delete stack template
POST   /api/stack-templates/{id}/create     — create project from stack template
GET    /api/projects/{id}/upgrades          — check module upgrades
POST   /api/admin/migrate-templates         — migrate YAML templates (admin only)
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from backend.db.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stacks"])
upgrades_router = APIRouter(prefix="/api/projects", tags=["stacks"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Lazy loaders
# ---------------------------------------------------------------------------

def _load_core(filename: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent.parent / "core" / filename
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _schemas():
    full = "backend.api.schemas.stack_schemas"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent / "schemas" / "stack-schemas.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(401, "Not authenticated")
    return user


def _require_admin(user: dict) -> None:
    if "admin" not in user.get("roles", []):
        raise HTTPException(403, "Admin role required")


# ---------------------------------------------------------------------------
# Stack compose
# ---------------------------------------------------------------------------

@router.post("/api/stacks/compose", status_code=200)
async def compose_project(request: Request):
    """Generate HCL files for a project from a stack definition."""
    user = _require_auth(request)
    schemas = _schemas()
    body = schemas.ComposeProjectRequest(**(await request.json()))

    composer_mod = _load_core("stack-composer.py", "stack_composer")
    composer = composer_mod.StackComposer()

    from backend.core.config import get_settings
    workspace_dir = get_settings().working_dir / "composed" / body.project_id

    async with get_session() as session:
        result = await composer.compose_project(
            session=session,
            project_id=body.project_id,
            stack_definition=body.stack_definition.model_dump(),
            workspace_dir=workspace_dir,
            registry_url=body.registry_url,
        )

    return {
        "project_id": result.project_id,
        "generated_files": result.generated_files,
        "warnings": result.warnings,
    }


# ---------------------------------------------------------------------------
# Stack templates CRUD
# ---------------------------------------------------------------------------

@router.get("/api/stack-templates")
async def list_stack_templates(request: Request):
    user = _require_auth(request)
    from backend.db.models import StackTemplate  # type: ignore[attr-defined]

    async with get_session() as session:
        rows = (await session.execute(
            select(StackTemplate)
            .where(StackTemplate.org_id == user.get("org_id", ""))
            .order_by(StackTemplate.created_at.desc())
        )).scalars().all()
        return [_stack_summary(s) for s in rows]


@router.post("/api/stack-templates", status_code=201)
async def create_stack_template(request: Request):
    user = _require_auth(request)
    schemas = _schemas()
    body = schemas.CreateStackTemplateRequest(**(await request.json()))
    from backend.db.models import StackTemplate  # type: ignore[attr-defined]

    async with get_session() as session:
        # Check unique name within org
        existing = (await session.execute(
            select(StackTemplate).where(
                StackTemplate.org_id == user.get("org_id", ""),
                StackTemplate.name == body.name,
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(409, "Stack template name already exists")

        stack = StackTemplate(
            name=body.name,
            description=body.description,
            org_id=user.get("org_id", ""),
            definition_json=json.dumps(body.definition.model_dump()),
            tags=body.tags,
            created_by=user["user_id"],
        )
        session.add(stack)
        await session.flush()
        return _stack_summary(stack)


@router.get("/api/stack-templates/{stack_id}")
async def get_stack_template(stack_id: str, request: Request):
    _require_auth(request)
    async with get_session() as session:
        stack = await _get_stack_or_404(session, stack_id)
        return _stack_detail(stack)


@router.patch("/api/stack-templates/{stack_id}")
async def update_stack_template(stack_id: str, request: Request):
    _require_auth(request)
    schemas = _schemas()
    body = schemas.UpdateStackTemplateRequest(**(await request.json()))
    async with get_session() as session:
        stack = await _get_stack_or_404(session, stack_id)
        if body.name is not None:
            stack.name = body.name
        if body.description is not None:
            stack.description = body.description
        if body.definition is not None:
            stack.definition_json = json.dumps(body.definition.model_dump())
        if body.tags is not None:
            stack.tags = body.tags
        session.add(stack)
        await session.flush()
        return _stack_detail(stack)


@router.delete("/api/stack-templates/{stack_id}", status_code=204)
async def delete_stack_template(stack_id: str, request: Request):
    _require_auth(request)
    async with get_session() as session:
        stack = await _get_stack_or_404(session, stack_id)
        await session.delete(stack)


@router.post("/api/stack-templates/{stack_id}/create", status_code=201)
async def create_project_from_template(stack_id: str, request: Request):
    """Instantiate a new project using a saved stack template."""
    user = _require_auth(request)
    schemas = _schemas()
    body = schemas.CreateProjectFromTemplateRequest(**(await request.json()))

    async with get_session() as session:
        stack = await _get_stack_or_404(session, stack_id)
        definition = json.loads(stack.definition_json)

        # Apply variable overrides
        for mod in definition.get("modules", []):
            for k, v in body.variable_overrides.items():
                if k in mod.get("variables", {}):
                    mod["variables"][k] = v

        composer_mod = _load_core("stack-composer.py", "stack_composer")
        composer = composer_mod.StackComposer()

        from backend.core.config import get_settings
        import uuid
        project_id = str(uuid.uuid4())
        workspace_dir = get_settings().working_dir / "composed" / project_id

        result = await composer.compose_project(
            session=session,
            project_id=project_id,
            stack_definition=definition,
            workspace_dir=workspace_dir,
        )
        return {
            "project_id": project_id,
            "stack_template_id": stack_id,
            "generated_files": result.generated_files,
            "warnings": result.warnings,
        }


# ---------------------------------------------------------------------------
# Module upgrade check
# ---------------------------------------------------------------------------

@upgrades_router.get("/{project_id}/upgrades")
async def check_module_upgrades(project_id: str, request: Request):
    """Check if any registry modules used in a project have newer versions."""
    user = _require_auth(request)
    from backend.db.models import Project  # type: ignore[attr-defined]

    async with get_session() as session:
        project = (await session.execute(
            select(Project).where(Project.id == project_id)
        )).scalar_one_or_none()
        if not project:
            raise HTTPException(404, "Project not found")

        # If project has a stack definition stored in config_yaml, parse it
        definition: dict = {}
        if project.config_yaml:
            try:
                import yaml
                parsed = yaml.safe_load(project.config_yaml)
                if isinstance(parsed, dict) and "modules" in parsed:
                    definition = parsed
            except Exception:
                pass

        if not definition:
            return []

        composer_mod = _load_core("stack-composer.py", "stack_composer")
        composer = composer_mod.StackComposer()
        upgrades = await composer.check_upgrades(session, definition, user.get("org_id", ""))
        return [
            {
                "module_name": u.module_name,
                "current_version": u.current_version,
                "latest_version": u.latest_version,
                "source": u.source,
            }
            for u in upgrades
        ]


# ---------------------------------------------------------------------------
# Admin: migrate YAML templates
# ---------------------------------------------------------------------------

@admin_router.post("/migrate-templates")
async def migrate_templates(request: Request):
    """Migrate all YAML project templates to registry modules + stack templates."""
    user = _require_auth(request)
    _require_admin(user)

    migrator_mod = _load_core("template-migrator.py", "template_migrator")
    migrator = migrator_mod.TemplateMigrator()

    async with get_session() as session:
        results = await migrator.migrate_all(session, org_id=user.get("org_id", ""), user_id=user["user_id"])

    return {
        "migrated": len([r for r in results if r.success]),
        "failed": len([r for r in results if not r.success]),
        "results": [
            {
                "template_name": r.template_name,
                "success": r.success,
                "stack_template_id": r.stack_template_id,
                "modules_created": r.modules_created,
                "error": r.error,
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_stack_or_404(session, stack_id: str):
    from backend.db.models import StackTemplate  # type: ignore[attr-defined]

    stack = (await session.execute(
        select(StackTemplate).where(StackTemplate.id == stack_id)
    )).scalar_one_or_none()
    if not stack:
        raise HTTPException(404, "Stack template not found")
    return stack


def _stack_summary(s) -> dict:
    definition = json.loads(s.definition_json or "{}")
    module_count = len(definition.get("modules", []))
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "org_id": s.org_id,
        "tags": s.tags or [],
        "created_by": s.created_by,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
        "module_count": module_count,
    }


def _stack_detail(s) -> dict:
    return {
        **_stack_summary(s),
        "definition_json": s.definition_json,
    }
