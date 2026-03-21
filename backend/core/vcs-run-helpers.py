"""DB persistence helpers and plan formatting for VCS runs (Phase 3).

Extracted from vcs-run-manager to keep file sizes under 200 lines.

Provides:
  _find_vcs_conn_by_repo            — lookup VCSConnection + Workspace by repo
  _find_vcs_conn_by_repo_and_branch — lookup with branch filter
  _create_job_record                — persist a VCS-triggered Job
  _create_approval_record           — persist an Approval for manual gating
  _format_plan_summary              — convert PlanResult to markdown
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from backend.db.database import get_session
from backend.db.models import Approval, Job, VCSConnection

logger = logging.getLogger(__name__)


async def find_vcs_conn_by_repo(repo: str) -> tuple[Any, Any]:
    """Return (workspace, vcs_conn) for the first matching repo, or (None, None)."""
    from sqlalchemy import select
    from backend.db.models import Workspace

    async with get_session() as session:
        result = await session.execute(
            select(VCSConnection)
            .where(VCSConnection.repo_full_name == repo)
            .limit(1)
        )
        vcs_conn = result.scalar_one_or_none()
        if not vcs_conn:
            return None, None
        workspace = await session.get(Workspace, vcs_conn.workspace_id)
        return workspace, vcs_conn


async def find_vcs_conn_by_repo_and_branch(repo: str, branch: str) -> tuple[Any, Any]:
    """Return (workspace, vcs_conn) for a specific repo+branch, or (None, None)."""
    from sqlalchemy import select
    from backend.db.models import Workspace

    async with get_session() as session:
        result = await session.execute(
            select(VCSConnection)
            .where(
                VCSConnection.repo_full_name == repo,
                VCSConnection.branch == branch,
            )
            .limit(1)
        )
        vcs_conn = result.scalar_one_or_none()
        if not vcs_conn:
            return None, None
        workspace = await session.get(Workspace, vcs_conn.workspace_id)
        return workspace, vcs_conn


async def create_job_record(
    *,
    job_type: str,
    status: str,
    workspace_dir: str,
    commit_sha: str,
    pr_number: int | None,
    trigger: str,
    output: str,
) -> None:
    """Insert a Job row with VCS metadata."""
    async with get_session() as session:
        job = Job(
            id=str(uuid.uuid4()),
            type=job_type,
            status=status,
            workspace_dir=workspace_dir,
            vcs_commit_sha=commit_sha,
            vcs_pr_number=pr_number,
            vcs_trigger=trigger,
            output=output,
        )
        session.add(job)


async def create_approval_record(workspace_name: str, plan_summary: str) -> None:
    """Insert a pending Approval row for a VCS-triggered plan."""
    async with get_session() as session:
        approval = Approval(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            workspace=workspace_name,
            status="pending",
            plan_summary_json=json.dumps([plan_summary]),
        )
        session.add(approval)


def format_plan_summary(plan_result: Any) -> str:
    """Convert a TerraformRunner PlanResult into a compact markdown summary."""
    try:
        changes = getattr(plan_result, "resource_changes", [])
        to_add     = sum(1 for c in changes if "create" in str(getattr(c, "action", "")))
        to_change  = sum(1 for c in changes if "update" in str(getattr(c, "action", "")))
        to_destroy = sum(1 for c in changes if "delete" in str(getattr(c, "action", "")))
        lines = "\n".join(
            f"- `{getattr(c, 'address', '?')}` — {getattr(c, 'action', '?')}"
            for c in changes
        )
        return (
            f"**Plan:** {to_add} to add, {to_change} to change, {to_destroy} to destroy\n\n"
            f"<details><summary>Resource changes</summary>\n\n{lines}\n</details>"
        )
    except Exception:
        logger.warning("Could not format plan summary", exc_info=True)
        return "Plan output unavailable."
