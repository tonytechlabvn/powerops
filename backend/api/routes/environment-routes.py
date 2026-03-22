"""Environment management routes (Phase 2).

POST   /api/environments                          — create environment
GET    /api/environments                          — list environments (org-scoped via ?org_id=)
GET    /api/environments/{id}                     — get environment detail
PATCH  /api/environments/{id}                     — update environment
DELETE /api/environments/{id}                     — delete environment
GET    /api/environments/{id}/variables           — list env variables
POST   /api/environments/{id}/variables           — set/upsert variable
DELETE /api/environments/{id}/variables/{key}     — delete variable
GET    /api/environments/{id}/workspaces          — list workspaces in environment
POST   /api/environments/{id}/workspaces/{ws_id}  — link workspace to environment
GET    /api/workspaces/{ws_id}/effective-variables — merged env+workspace vars
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Query

from backend.db.database import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["environments"])

_CORE_DIR = _P(__file__).resolve().parent.parent.parent / "core"
_SCHEMAS_DIR = _P(__file__).resolve().parent.parent / "schemas"


def _load(filename: str, alias: str):
    full = f"backend.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    path = _CORE_DIR / filename if filename.endswith(".py") and "core" in alias else _SCHEMAS_DIR / filename
    spec = _ilu.spec_from_file_location(full, path)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _svc():
    mod = _load("environment-service.py", "core.environment_service")
    return mod.EnvironmentService()


def _schemas():
    return _load("environment-schemas.py", "api.schemas.environment_schemas")


# ---------------------------------------------------------------------------
# Environment CRUD
# ---------------------------------------------------------------------------

@router.post("/environments", status_code=201)
async def create_environment(body: dict):
    """Create a new environment scoped to an org."""
    s = _schemas()
    req = s.CreateEnvironmentRequest(**body)
    async with get_session() as session:
        try:
            result = await _svc().create_environment(
                session,
                org_id=req.org_id,
                name=req.name,
                description=req.description,
                color=req.color,
                is_protected=req.is_protected,
                auto_apply=req.auto_apply,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/environments")
async def list_environments(org_id: str = Query(..., description="Filter by organization ID")):
    """List all environments for an org."""
    async with get_session() as session:
        return await _svc().list_environments(session, org_id)


@router.get("/environments/{env_id}")
async def get_environment(env_id: str):
    """Return a single environment with variable and workspace counts."""
    async with get_session() as session:
        try:
            return await _svc().get_environment(session, env_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/environments/{env_id}")
async def update_environment(env_id: str, body: dict):
    """Partially update environment fields."""
    s = _schemas()
    req = s.UpdateEnvironmentRequest(**body)
    async with get_session() as session:
        try:
            return await _svc().update_environment(session, env_id, **req.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/environments/{env_id}", status_code=204)
async def delete_environment(env_id: str, force: bool = Query(False)):
    """Delete an environment. Set force=true to delete protected environments."""
    async with get_session() as session:
        try:
            await _svc().delete_environment(session, env_id, force=force)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Variable management
# ---------------------------------------------------------------------------

@router.get("/environments/{env_id}/variables")
async def list_env_variables(env_id: str, reveal: bool = Query(False)):
    """List variables for an environment. Sensitive values masked unless reveal=true."""
    async with get_session() as session:
        return await _svc().get_variables(session, env_id, reveal=reveal)


@router.post("/environments/{env_id}/variables", status_code=201)
async def set_env_variable(env_id: str, body: dict):
    """Create or update a variable in this environment."""
    s = _schemas()
    req = s.SetVariableRequest(**body)
    async with get_session() as session:
        return await _svc().set_variable(
            session, env_id,
            key=req.key, value=req.value,
            is_sensitive=req.is_sensitive, is_hcl=req.is_hcl,
            category=req.category, description=req.description,
        )


@router.delete("/environments/{env_id}/variables/{key}", status_code=204)
async def delete_env_variable(env_id: str, key: str):
    """Remove a variable from this environment."""
    async with get_session() as session:
        await _svc().delete_variable(session, env_id, key)


# ---------------------------------------------------------------------------
# Workspace linking
# ---------------------------------------------------------------------------

@router.get("/environments/{env_id}/workspaces")
async def list_environment_workspaces(env_id: str):
    """List all workspaces assigned to this environment."""
    async with get_session() as session:
        return await _svc().get_environment_workspaces(session, env_id)


@router.post("/environments/{env_id}/workspaces/{workspace_id}", status_code=204)
async def link_workspace_to_environment(env_id: str, workspace_id: str):
    """Assign a workspace to this environment."""
    async with get_session() as session:
        try:
            await _svc().link_workspace(session, workspace_id, env_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Effective variables (inheritance chain)
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/effective-variables")
async def get_effective_variables(workspace_id: str, reveal: bool = Query(False)):
    """Return merged env+workspace variables for a workspace (workspace overrides env)."""
    async with get_session() as session:
        return await _svc().get_effective_variables(session, workspace_id, reveal=reveal)
