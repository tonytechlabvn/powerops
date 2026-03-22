"""Variable set workspace assignment routes.

POST   /api/variable-sets/{id}/assign/{workspace_id} — assign to workspace
DELETE /api/variable-sets/{id}/assign/{workspace_id} — unassign from workspace
GET    /api/variable-sets/{id}/workspaces            — list assigned workspaces
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


class _AssignBody(BaseModel):
    priority: int = 0


@router.post("/{vs_id}/assign/{workspace_id}", status_code=201)
async def assign_to_workspace(vs_id: str, workspace_id: str, body: _AssignBody):
    """Attach a variable set to a workspace with optional priority ordering."""
    try:
        await _mgr().assign_to_workspace(vs_id, workspace_id, priority=body.priority)
        return _s().WorkspaceAssignmentResponse(
            variable_set_id=vs_id, workspace_id=workspace_id, priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{vs_id}/assign/{workspace_id}", status_code=204)
async def unassign_from_workspace(vs_id: str, workspace_id: str):
    """Detach a variable set from a workspace."""
    try:
        await _mgr().unassign_from_workspace(vs_id, workspace_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{vs_id}/workspaces")
async def list_assigned_workspaces(vs_id: str):
    """List all workspaces that have this variable set assigned."""
    try:
        from backend.db.database import get_session
        from backend.db.models import VariableSetAssignment, Workspace
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            rows = (await session.execute(
                sa_select(VariableSetAssignment, Workspace)
                .join(Workspace, Workspace.id == VariableSetAssignment.workspace_id)
                .where(VariableSetAssignment.variable_set_id == vs_id)
                .order_by(VariableSetAssignment.priority.desc())
            )).all()

        return {
            "workspaces": [
                {
                    "workspace_id": a.workspace_id,
                    "workspace_name": w.name,
                    "priority": a.priority,
                }
                for a, w in rows
            ]
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
