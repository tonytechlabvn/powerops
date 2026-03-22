"""VCS workflow management routes (Phase 4).

GET    /api/workspaces/{workspace_id}/vcs-workflow              — get current config
PATCH  /api/workspaces/{workspace_id}/vcs-workflow              — update trigger patterns
GET    /api/workspaces/{workspace_id}/vcs-workflow/pr-plans     — list PR plan runs
GET    /api/workspaces/{workspace_id}/vcs-workflow/pr-plans/{pr_number} — get plans for PR
POST   /api/workspaces/{workspace_id}/vcs-workflow/pr-plans/{pr_number}/replan — manual replan
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException

from backend.db.database import get_session
from backend.db.models import VCSConnection, Workspace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workspaces/{workspace_id}/vcs-workflow", tags=["vcs-workflow"])

_CORE_DIR = _P(__file__).resolve().parent.parent.parent / "core"
_SCHEMAS_DIR = _P(__file__).resolve().parent.parent / "schemas"


def _load_core(filename: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _CORE_DIR / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_schemas():
    alias = "backend.api.schemas.vcs_plan_schemas"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(alias, _SCHEMAS_DIR / "vcs-plan-schemas.py")
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _plan_runner():
    mod = _load_core("vcs-plan-runner.py", "vcs_plan_runner")
    return mod.VCSPlanRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_workspace_and_vcs(workspace_id: str, session):
    """Return (workspace, vcs_conn) or raise 404."""
    from sqlalchemy import select
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    result = await session.execute(
        select(VCSConnection).where(VCSConnection.workspace_id == workspace_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No VCS connection for this workspace")
    return ws, conn


# ---------------------------------------------------------------------------
# Workflow config endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def get_vcs_workflow_config(workspace_id: str):
    """Return current VCS workflow configuration including trigger patterns."""
    s = _load_schemas()
    async with get_session() as session:
        ws, conn = await _get_workspace_and_vcs(workspace_id, session)
        patterns = [
            s.TriggerPatternItem(**p)
            for p in (conn.trigger_patterns or [{"branch": "main", "action": "apply"}, {"branch": "*", "action": "plan"}])
        ]
        return s.VCSWorkflowConfigResponse(
            workspace_id=workspace_id,
            repo_full_name=conn.repo_full_name,
            branch=conn.branch,
            auto_apply=conn.auto_apply,
            trigger_patterns=patterns,
        )


@router.patch("")
async def update_vcs_workflow_config(workspace_id: str, body: dict):
    """Update trigger patterns and/or auto_apply setting."""
    s = _load_schemas()
    req = s.VCSWorkflowConfigRequest(**body)
    async with get_session() as session:
        ws, conn = await _get_workspace_and_vcs(workspace_id, session)
        conn.trigger_patterns = [p.model_dump() for p in req.trigger_patterns]
        if req.auto_apply is not None:
            conn.auto_apply = req.auto_apply
        await session.flush()
        await session.refresh(conn)
        return s.VCSWorkflowConfigResponse(
            workspace_id=workspace_id,
            repo_full_name=conn.repo_full_name,
            branch=conn.branch,
            auto_apply=conn.auto_apply,
            trigger_patterns=req.trigger_patterns,
        )


# ---------------------------------------------------------------------------
# PR plan run endpoints
# ---------------------------------------------------------------------------

@router.get("/pr-plans")
async def list_pr_plans(workspace_id: str):
    """List all VCS-triggered plan runs for this workspace across all PRs."""
    from sqlalchemy import select
    from backend.db.models import VCSPlanRun
    async with get_session() as session:
        ws, conn = await _get_workspace_and_vcs(workspace_id, session)
        stmt = (
            select(VCSPlanRun)
            .where(VCSPlanRun.vcs_connection_id == conn.id)
            .order_by(VCSPlanRun.triggered_at.desc())
            .limit(100)
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [_plan_runner()._run_to_dict(r) for r in rows]


@router.get("/pr-plans/{pr_number}")
async def get_pr_plan_runs(workspace_id: str, pr_number: int):
    """List all plan runs for a specific PR number."""
    async with get_session() as session:
        ws, conn = await _get_workspace_and_vcs(workspace_id, session)
    return await _plan_runner().get_pr_plans(conn.id, pr_number)


@router.post("/pr-plans/{pr_number}/replan", status_code=202)
async def trigger_manual_replan(workspace_id: str, pr_number: int, body: dict | None = None):
    """Manually trigger a new speculative plan for a PR."""
    from backend.core.config import get_settings
    s = _load_schemas()
    req = s.ReplanRequest(**(body or {}))

    async with get_session() as session:
        ws, conn = await _get_workspace_and_vcs(workspace_id, session)

        # Resolve commit SHA: use provided or fetch from GitHub
        commit_sha = req.commit_sha
        if not commit_sha:
            try:
                gh_mod = _load_core("github-app-client.py", "github_app_client")
                token = await gh_mod.get_installation_token(conn.installation_id)
                pr_info = await gh_mod.get_pr_info(conn.repo_full_name, pr_number, token)
                commit_sha = pr_info["head"]["sha"]
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Failed to fetch PR info: {exc}") from exc

        run = await _plan_runner().trigger_plan(
            vcs_connection_id=conn.id,
            workspace_id=workspace_id,
            workspace_name=ws.name,
            repo_full_name=conn.repo_full_name,
            working_directory=conn.working_directory,
            installation_id=conn.installation_id,
            pr_number=pr_number,
            commit_sha=commit_sha,
            branch=conn.branch,
        )
    return {"run_id": run["id"], "status": "queued", "commit_sha": commit_sha}
