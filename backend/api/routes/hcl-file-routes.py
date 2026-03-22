"""HCL file CRUD routes — list/read/write/delete/rename/validate workspace files.

Search and directory routes live in hcl-directory-routes.py.
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/workspaces/{workspace_id}/files", tags=["hcl-files"])


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


def _schemas():
    return _load_schema("hcl-file-schemas.py", "hcl_file_schemas")


def _file_manager_cls():
    return _load_core("hcl-file-manager.py", "hcl_file_manager").HCLFileManager


async def _get_workspace_dir(workspace_id: str) -> _Path:
    """Fetch workspace directory from DB by workspace ID or name."""
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


def _mgr(workspace_dir: _Path):
    return _file_manager_cls()(workspace_dir)


def _map_validation(v) -> dict | None:
    if v is None:
        return None
    s = _schemas()
    return s.ValidationResponse(valid=v.valid, errors=v.errors, warnings=v.warnings).model_dump()


class _WriteBody(BaseModel):
    content: str
    expected_checksum: str | None = None


class _RenameBody(BaseModel):
    new_path: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", tags=["hcl-files"])
async def list_workspace_files(workspace_id: str, pattern: str = "**/*"):
    """List all workspace files matching pattern."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        files = await _mgr(ws_dir).list_files(pattern)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    s = _schemas()
    return s.FileTreeResponse(
        workspace_id=workspace_id,
        files=[s.FileInfoResponse(
            path=f.path, name=f.name, size=f.size,
            modified_at=f.modified_at, is_directory=f.is_directory, checksum=f.checksum,
        ) for f in files],
    )


@router.get("/{path:path}", tags=["hcl-files"])
async def read_workspace_file(workspace_id: str, path: str):
    """Read the content of a single workspace file."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        fc = await _mgr(ws_dir).read_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, IsADirectoryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    s = _schemas()
    return s.FileContentResponse(
        path=fc.path, content=fc.content, checksum=fc.checksum,
        size=fc.size, language=fc.language,
    )


@router.post("/{path:path}/rename", tags=["hcl-files"])
async def rename_workspace_file(workspace_id: str, path: str, body: _RenameBody):
    """Rename or move a file within the workspace."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        await _mgr(ws_dir).rename_file(path, body.new_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (FileExistsError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"old_path": path, "new_path": body.new_path}


@router.post("/{path:path}/validate", tags=["hcl-files"])
async def validate_workspace_file(workspace_id: str, path: str, body: _WriteBody):
    """Validate HCL content without saving to disk."""
    await _get_workspace_dir(workspace_id)
    if not path.endswith(".tf"):
        raise HTTPException(status_code=422, detail="Only .tf files can be validated.")
    try:
        from backend.core import hcl_validator
        result = hcl_validator.validate_syntax(body.content)
        return _schemas().ValidationResponse(valid=result.valid, errors=result.errors, warnings=[])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{path:path}", status_code=201, tags=["hcl-files"])
async def create_workspace_file(workspace_id: str, path: str, body: _WriteBody):
    """Create a new file in the workspace."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        result = await _mgr(ws_dir).write_file(path, body.content, body.expected_checksum)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    s = _schemas()
    val = s.ValidationResponse(**_map_validation(result.validation)) if result.validation else None
    return s.WriteFileResponse(path=result.path, checksum=result.checksum, validation=val)


@router.put("/{path:path}", tags=["hcl-files"])
async def update_workspace_file(workspace_id: str, path: str, body: _WriteBody):
    """Update an existing file's content."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        result = await _mgr(ws_dir).write_file(path, body.content, body.expected_checksum)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    s = _schemas()
    val = s.ValidationResponse(**_map_validation(result.validation)) if result.validation else None
    return s.WriteFileResponse(path=result.path, checksum=result.checksum, validation=val)


@router.delete("/{path:path}", status_code=204, tags=["hcl-files"])
async def delete_workspace_file(workspace_id: str, path: str):
    """Delete a file from the workspace."""
    ws_dir = await _get_workspace_dir(workspace_id)
    try:
        await _mgr(ws_dir).delete_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (IsADirectoryError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
