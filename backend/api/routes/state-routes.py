"""Terraform HTTP state backend routes + management API (Phase 1).

Terraform-native endpoints (workspace param = workspace NAME):
  GET    /api/state/{workspace}              — pull current state
  POST   /api/state/{workspace}             — push new state (?ID=lock_id)
  DELETE /api/state/{workspace}             — delete all state versions
  POST   /api/state/{workspace}/lock        — acquire lock
  POST   /api/state/{workspace}/unlock      — release lock

Management endpoints:
  GET    /api/state/{workspace}/versions            — paginated version list
  GET    /api/state/{workspace}/versions/{serial}   — specific version bytes
  POST   /api/state/{workspace}/rollback/{serial}   — rollback to serial
  DELETE /api/state/{workspace}/lock                — force-unlock
  GET    /api/state/{workspace}/outputs             — workspace outputs
"""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select

from backend.db.database import get_session
from backend.db.models import StateVersion, Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/state", tags=["state"])


# ---------------------------------------------------------------------------
# Kebab-case module loaders
# ---------------------------------------------------------------------------

def _load_state_manager():
    alias = "backend.core.state_manager"
    if alias in sys.modules:
        return sys.modules[alias]
    mod_path = Path(__file__).parent.parent.parent / "core" / "state-manager.py"
    spec = importlib.util.spec_from_file_location(alias, mod_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _mgr():
    return _load_state_manager()


# ---------------------------------------------------------------------------
# Internal: resolve workspace name → workspace_id
# ---------------------------------------------------------------------------

async def _resolve_workspace_id(name: str) -> str:
    """Lookup workspace by name, raise 404 if missing."""
    async with get_session() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.name == name)
        )
        ws = result.scalar_one_or_none()
        if ws is None:
            raise HTTPException(status_code=404, detail=f"Workspace '{name}' not found.")
        ws_id = ws.id
    return ws_id


# ---------------------------------------------------------------------------
# Terraform HTTP backend endpoints
# ---------------------------------------------------------------------------

@router.get("/{workspace}")
async def pull_state(workspace: str) -> Response:
    """Return current state as raw JSON bytes (Terraform GET state)."""
    workspace_id = await _resolve_workspace_id(workspace)
    state_bytes = await _mgr().pull_state(workspace_id)
    if state_bytes is None:
        # Terraform expects 200 with empty body or a valid empty state, not 404
        return Response(content=b"", media_type="application/json", status_code=200)
    return Response(content=state_bytes, media_type="application/json", status_code=200)


@router.post("/{workspace}")
async def push_state(
    workspace: str,
    request: Request,
    ID: str = Query(default="", alias="ID"),  # noqa: N803 — Terraform sends ?ID=
) -> Response:
    """Accept raw state bytes from Terraform POST state push."""
    workspace_id = await _resolve_workspace_id(workspace)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty state body.")

    # Extract user identity from request state (set by auth middleware)
    user = getattr(request.state, "user", "terraform")

    try:
        await _mgr().push_state(
            workspace_id=workspace_id,
            state_bytes=body,
            lock_id=ID or None,
            user=user,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to push state for workspace %s: %s", workspace, exc)
        raise HTTPException(status_code=500, detail="Failed to store state.")

    return Response(status_code=200)


@router.delete("/{workspace}", status_code=200)
async def delete_state(workspace: str) -> dict:
    """Delete all state versions for a workspace."""
    workspace_id = await _resolve_workspace_id(workspace)
    async with get_session() as session:
        await session.execute(
            delete(StateVersion).where(StateVersion.workspace_id == workspace_id)
        )
    logger.info("All state versions deleted for workspace %s", workspace)
    return {"deleted": True}


@router.post("/{workspace}/lock")
async def lock_workspace(workspace: str, request: Request) -> Response:
    """Acquire state lock. Returns 423 if already locked."""
    workspace_id = await _resolve_workspace_id(workspace)

    try:
        body = await request.body()
        lock_info = json.loads(body) if body else {}
    except Exception:
        lock_info = {}

    try:
        result = await _mgr().acquire_lock(workspace_id, lock_info)
    except HTTPException as exc:
        if exc.status_code == 423:
            return JSONResponse(status_code=423, content=exc.detail)
        raise

    return JSONResponse(status_code=200, content=result)


@router.post("/{workspace}/unlock")
async def unlock_workspace(workspace: str, request: Request) -> Response:
    """Release state lock. Returns 409 if lock_id doesn't match."""
    workspace_id = await _resolve_workspace_id(workspace)

    try:
        body = await request.body()
        lock_info = json.loads(body) if body else {}
    except Exception:
        lock_info = {}

    lock_id = lock_info.get("ID", "")
    released = await _mgr().release_lock(workspace_id, lock_id)
    if not released:
        return JSONResponse(
            status_code=409,
            content={"detail": "Lock not found or lock ID mismatch."},
        )
    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Management endpoints
# ---------------------------------------------------------------------------

@router.get("/{workspace}/versions")
async def list_versions(
    workspace: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Return paginated list of state versions (metadata only, no raw data)."""
    workspace_id = await _resolve_workspace_id(workspace)
    versions = await _mgr().list_versions(workspace_id, limit=limit, offset=offset)
    return {"workspace": workspace, "versions": versions, "limit": limit, "offset": offset}


@router.get("/{workspace}/versions/{serial}")
async def get_state_version(workspace: str, serial: int) -> Response:
    """Return raw state bytes for a specific serial number."""
    workspace_id = await _resolve_workspace_id(workspace)
    state_bytes = await _mgr().pull_state_version(workspace_id, serial)
    if state_bytes is None:
        raise HTTPException(
            status_code=404, detail=f"State serial {serial} not found for workspace '{workspace}'."
        )
    return Response(content=state_bytes, media_type="application/json", status_code=200)


@router.post("/{workspace}/rollback/{serial}")
async def rollback_state(workspace: str, serial: int, request: Request) -> dict:
    """Rollback workspace state to a previous serial version."""
    workspace_id = await _resolve_workspace_id(workspace)
    user = getattr(request.state, "user", "system")

    try:
        version = await _mgr().rollback_state(workspace_id, serial, user=user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Rollback failed for workspace %s serial %s: %s", workspace, serial, exc)
        raise HTTPException(status_code=500, detail="Rollback failed.")

    return {
        "workspace": workspace,
        "rolled_back_to_serial": serial,
        "new_version_id": version.id,
    }


@router.delete("/{workspace}/lock", status_code=200)
async def force_unlock(workspace: str) -> dict:
    """Force-release any lock on a workspace (admin operation)."""
    workspace_id = await _resolve_workspace_id(workspace)
    released = await _mgr().force_unlock(workspace_id)
    return {"workspace": workspace, "force_unlocked": released}


@router.get("/{workspace}/outputs")
async def get_outputs(workspace: str) -> dict:
    """Return non-sensitive outputs from the latest workspace state."""
    workspace_id = await _resolve_workspace_id(workspace)
    outputs = await _mgr().get_outputs(workspace_id)
    return {"workspace": workspace, "outputs": outputs}
