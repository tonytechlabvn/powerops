"""Workspace management routes.

POST   /api/workspaces              — create workspace
GET    /api/workspaces              — list workspaces
GET    /api/workspaces/current      — get current workspace
GET    /api/workspaces/{name}       — get state summary
POST   /api/workspaces/{name}/switch — switch to workspace
DELETE /api/workspaces/{name}       — delete workspace
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    provider: str = ""
    environment: str = ""


class WorkspaceResponse(BaseModel):
    name: str
    provider: str = ""
    environment: str = ""
    workspace_dir: str = ""
    created_at: str = ""
    last_used: str = ""


class StateSummaryResponse(BaseModel):
    name: str
    resource_count: int = 0
    resources: list[dict] = []
    error: str = ""


def _load_manager():
    import importlib.util as ilu
    import sys
    from pathlib import Path

    alias = "backend.core.workspace_manager"
    if alias in sys.modules:
        return sys.modules[alias]
    core_dir = Path(__file__).parent.parent.parent / "core"
    spec = ilu.spec_from_file_location(alias, core_dir / "workspace-manager.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _mgr():
    from backend.core.config import get_settings
    mod = _load_manager()
    settings = get_settings()
    return mod.WorkspaceManager(base_dir=settings.working_dir)


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(body: CreateWorkspaceRequest) -> WorkspaceResponse:
    """Create a new workspace directory and register it in the database."""
    result = await _mgr().create(
        name=body.name,
        provider=body.provider,
        environment=body.environment,
    )
    return WorkspaceResponse(**result)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces() -> list[WorkspaceResponse]:
    """List all registered workspaces."""
    items = await _mgr().list_workspaces()
    return [WorkspaceResponse(**w) for w in items]


@router.get("/current", response_model=WorkspaceResponse)
async def get_current_workspace() -> WorkspaceResponse:
    """Return the currently active workspace."""
    result = await _mgr().get_current()
    return WorkspaceResponse(**result)


@router.get("/{name}/state", response_model=StateSummaryResponse)
async def get_state_summary(name: str) -> StateSummaryResponse:
    """Return a terraform state resource summary for the named workspace."""
    result = await _mgr().get_state_summary(name)
    return StateSummaryResponse(**result)


@router.post("/{name}/switch", response_model=WorkspaceResponse)
async def switch_workspace(name: str) -> WorkspaceResponse:
    """Switch the active terraform workspace."""
    result = await _mgr().switch(name)
    return WorkspaceResponse(**result)


@router.delete("/{name}", status_code=204)
async def delete_workspace(name: str) -> None:
    """Delete a workspace and remove its directory."""
    await _mgr().delete(name)
