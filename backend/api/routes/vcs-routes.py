"""VCS connection management routes (Phase 3).

POST/GET/PATCH/DELETE /api/workspaces/{workspace_id}/vcs — CRUD for VCS connections
GET /api/vcs/github/setup     — GitHub App manifest URL
GET /api/vcs/github/callback  — manifest flow callback handler
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.database import get_session
from backend.db.models import VCSConnection, Workspace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["vcs"])


def _load_schemas():
    alias = "backend.api.schemas.vcs_schemas"
    if alias in _sys.modules:
        return _sys.modules[alias]
    schemas_dir = _P(__file__).resolve().parent.parent / "schemas"
    spec = _ilu.spec_from_file_location(alias, schemas_dir / "vcs-schemas.py")
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_workspace_or_404(workspace_id: str):
    async with get_session() as session:
        ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


async def _get_vcs_conn_or_404(workspace_id: str):
    async with get_session() as session:
        stmt = select(VCSConnection).where(
            VCSConnection.workspace_id == workspace_id
        )
        result = await session.execute(stmt)
        conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No VCS connection for this workspace")
    return conn


# ---------------------------------------------------------------------------
# VCS connection CRUD
# ---------------------------------------------------------------------------

@router.post("/workspaces/{workspace_id}/vcs", status_code=201)
async def connect_vcs(workspace_id: str, body: dict):
    """Connect a workspace to a GitHub repository via GitHub App installation."""
    schemas = _load_schemas()
    req = schemas.VCSConnectRequest(**body)

    # Verify workspace exists
    await _get_workspace_or_404(workspace_id)

    async with get_session() as session:
        # Prevent duplicate connections
        existing = await session.execute(
            select(VCSConnection).where(VCSConnection.workspace_id == workspace_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail="Workspace already has a VCS connection"
            )

        conn = VCSConnection(
            workspace_id=workspace_id,
            installation_id=req.installation_id,
            repo_full_name=req.repo_full_name,
            branch=req.branch,
            working_directory=req.working_directory,
            auto_apply=req.auto_apply,
            created_by="system",
        )
        session.add(conn)
        await session.flush()
        await session.refresh(conn)
        return schemas.VCSConnectionResponse.model_validate(conn)


@router.get("/workspaces/{workspace_id}/vcs")
async def get_vcs_connection(workspace_id: str):
    """Return the current VCS connection for a workspace."""
    schemas = _load_schemas()
    conn = await _get_vcs_conn_or_404(workspace_id)
    return schemas.VCSConnectionResponse.model_validate(conn)


@router.patch("/workspaces/{workspace_id}/vcs")
async def update_vcs_connection(workspace_id: str, body: dict):
    """Partially update VCS connection settings (branch, working_dir, auto_apply)."""
    schemas = _load_schemas()
    req = schemas.VCSUpdateRequest(**body)

    async with get_session() as session:
        stmt = select(VCSConnection).where(VCSConnection.workspace_id == workspace_id)
        result = await session.execute(stmt)
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="No VCS connection for this workspace")

        if req.branch is not None:
            conn.branch = req.branch
        if req.working_directory is not None:
            conn.working_directory = req.working_directory
        if req.auto_apply is not None:
            conn.auto_apply = req.auto_apply

        await session.flush()
        await session.refresh(conn)
        return schemas.VCSConnectionResponse.model_validate(conn)


@router.delete("/workspaces/{workspace_id}/vcs", status_code=204)
async def disconnect_vcs(workspace_id: str):
    """Remove the VCS connection from a workspace."""
    async with get_session() as session:
        stmt = select(VCSConnection).where(VCSConnection.workspace_id == workspace_id)
        result = await session.execute(stmt)
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="No VCS connection for this workspace")
        await session.delete(conn)


# ---------------------------------------------------------------------------
# GitHub App setup flow
# ---------------------------------------------------------------------------

@router.get("/vcs/github/setup")
async def github_app_setup():
    """Return the GitHub App manifest URL to begin the App creation flow."""
    schemas = _load_schemas()
    settings = get_settings()

    # If app already configured, return installation URL instead
    if settings.github_app_id:
        manifest_url = (
            f"https://github.com/apps/powerops-terrabot/installations/new"
        )
    else:
        # Manifest flow: redirect user to GitHub to create a new App
        manifest_url = (
            "https://github.com/settings/apps/new"
            "?state=powerops-setup"
        )

    return schemas.GitHubSetupResponse(manifest_url=manifest_url)


@router.get("/vcs/github/callback")
async def github_app_callback(code: str | None = None, state: str | None = None):
    """Exchange GitHub manifest code for App credentials and return them to the operator."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/app-manifests/{code}/conversions",
                headers={"Accept": "application/vnd.github+json"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("GitHub manifest conversion failed: %s", exc)
        raise HTTPException(status_code=502, detail="GitHub App creation failed")

    app_id = data.get("id")
    webhook_secret = data.get("webhook_secret", "")
    logger.info("GitHub App created via manifest flow: app_id=%s — set env vars and restart", app_id)

    return {
        "app_id": app_id,
        "message": (
            "Set TERRABOT_GITHUB_APP_ID, TERRABOT_GITHUB_PRIVATE_KEY, "
            "and TERRABOT_GITHUB_WEBHOOK_SECRET in your environment and restart TerraBot."
        ),
        # Hint only — never log the full secret
        "webhook_secret_hint": webhook_secret[:8] + "..." if webhook_secret else "",
    }
