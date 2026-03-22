"""HCL directory and search routes — extracted from hcl-file-routes.py.

POST   /api/workspaces/{workspace_id}/files/search             — content search
POST   /api/workspaces/{workspace_id}/directories              — create directory
DELETE /api/workspaces/{workspace_id}/directories/{path:path}  — delete directory
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# These routers are imported and registered in main.py alongside hcl-file-routes.
search_router = APIRouter(prefix="/api/workspaces/{workspace_id}/files", tags=["hcl-files"])
dir_router = APIRouter(prefix="/api/workspaces/{workspace_id}/directories", tags=["hcl-files"])


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


def _file_manager_cls():
    return _load_core("hcl-file-manager.py", "hcl_file_manager").HCLFileManager


def _schemas():
    return _load_schema("hcl-file-schemas.py", "hcl_file_schemas")


async def _get_workspace_dir(workspace_id: str) -> _Path:
    try:
        from backend.db.database import get_session
        from backend.db.models import Workspace
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            row = (await session.execute(
                sa_select(Workspace).where(Workspace.id == workspace_id)
            )).scalar_one_or_none()
            if row is None:
                row = (await session.execute(
                    sa_select(Workspace).where(Workspace.name == workspace_id)
                )).scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
            if not row.workspace_dir:
                raise HTTPException(status_code=422, detail="Workspace has no directory configured.")
            return _Path(row.workspace_dir)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc


def _mgr(ws_dir: _Path):
    return _file_manager_cls()(ws_dir)


class _SearchBody(BaseModel):
    query: str
    pattern: str = "**/*.tf"


class _DirectoryBody(BaseModel):
    path: str


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

@search_router.post("/search", tags=["hcl-files"])
async def search_workspace_files(workspace_id: str, body: _SearchBody):
    """Search file contents across the workspace."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        matches = await _mgr(ws_dir).search_files(body.query, body.pattern)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    s = _schemas()
    return {
        "query": body.query,
        "results": [
            s.SearchResultResponse(
                path=m.path, line=m.line, content=m.content,
                context_before=m.context_before, context_after=m.context_after,
            ).model_dump()
            for m in matches
        ],
    }


# ---------------------------------------------------------------------------
# Directory endpoints
# ---------------------------------------------------------------------------

@dir_router.post("", status_code=201, tags=["hcl-files"])
async def create_workspace_directory(workspace_id: str, body: _DirectoryBody):
    """Create a directory within the workspace."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        await _mgr(ws_dir).create_directory(body.path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"path": body.path, "created": True}


@dir_router.delete("/{path:path}", status_code=204, tags=["hcl-files"])
async def delete_workspace_directory(workspace_id: str, path: str):
    """Delete a directory tree within the workspace."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        await _mgr(ws_dir).delete_directory(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (NotADirectoryError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
