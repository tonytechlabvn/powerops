"""Variable set CRUD and variable management routes.

POST   /api/variable-sets                         — create set
GET    /api/variable-sets                         — list sets (org-scoped)
GET    /api/variable-sets/workspace/{ws_id}       — sets for a workspace
GET    /api/variable-sets/{id}                    — get set detail
PATCH  /api/variable-sets/{id}                    — update set
DELETE /api/variable-sets/{id}                    — delete set
POST   /api/variable-sets/{id}/variables          — add/update variable
DELETE /api/variable-sets/{id}/variables/{var_id} — delete variable

Workspace assignment routes live in variable-set-assignment-routes.py.
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/variable-sets", tags=["variable-sets"])


def _load_core(filename: str, alias: str):
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    core_dir = _Path(__file__).parent.parent.parent / "core"
    spec = _ilu.spec_from_file_location(full_name, core_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_schema(filename: str, alias: str):
    full_name = f"backend.api.schemas.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    schema_dir = _Path(__file__).parent.parent / "schemas"
    spec = _ilu.spec_from_file_location(full_name, schema_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _mgr():
    return _load_core("variable-set-manager.py", "variable_set_manager").VariableSetManager()


def _s():
    return _load_schema("variable-set-schemas.py", "variable_set_schemas")


def _to_response(data: dict):
    s = _s()
    return s.VariableSetResponse(
        id=data["id"], name=data["name"], description=data["description"],
        org_id=data["org_id"], is_global=data["is_global"],
        created_at=data["created_at"], updated_at=data["updated_at"],
        variable_count=data["variable_count"], workspace_count=data["workspace_count"],
        variables=[s.VariableSetVariable(**v) for v in data.get("variables", [])],
    )


class _CreateBody(BaseModel):
    name: str
    description: str = ""
    is_global: bool = False
    org_id: str = "default"


class _UpdateBody(BaseModel):
    name: str | None = None
    description: str | None = None


class _SetVarBody(BaseModel):
    key: str
    value: str
    category: str = "terraform"
    is_sensitive: bool = False
    is_hcl: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Variable set CRUD
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def create_variable_set(body: _CreateBody):
    """Create a new org-scoped variable set."""
    try:
        return _to_response(await _mgr().create(
            org_id=body.org_id, name=body.name,
            description=body.description, is_global=body.is_global,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("")
async def list_variable_sets(org_id: str = "default"):
    """List all variable sets for an organisation."""
    try:
        return {"variable_sets": [_to_response(r) for r in await _mgr().list_sets(org_id)]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/workspace/{workspace_id}")
async def get_workspace_variable_sets(workspace_id: str):
    """Get all variable sets attached to a specific workspace."""
    try:
        return {"variable_sets": [_to_response(r) for r in await _mgr().get_workspace_assignments(workspace_id)]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{vs_id}")
async def get_variable_set(vs_id: str):
    """Get full detail including variables."""
    try:
        return _to_response(await _mgr().get_set(vs_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/{vs_id}")
async def update_variable_set(vs_id: str, body: _UpdateBody):
    """Update variable set name or description."""
    try:
        return _to_response(await _mgr().update(vs_id, name=body.name, description=body.description))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{vs_id}", status_code=204)
async def delete_variable_set(vs_id: str):
    """Delete a variable set and all its variables and assignments."""
    try:
        await _mgr().delete(vs_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Variable management
# ---------------------------------------------------------------------------

@router.post("/{vs_id}/variables", status_code=201)
async def set_variable(vs_id: str, body: _SetVarBody):
    """Add or update a variable within a variable set."""
    try:
        result = await _mgr().set_variable(
            vs_id=vs_id, key=body.key, value=body.value,
            category=body.category, is_sensitive=body.is_sensitive,
            is_hcl=body.is_hcl, description=body.description,
        )
        return _s().VariableSetVariable(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{vs_id}/variables/{var_id}", status_code=204)
async def delete_variable(vs_id: str, var_id: str):
    """Delete a variable from a variable set."""
    try:
        await _mgr().delete_variable(var_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
