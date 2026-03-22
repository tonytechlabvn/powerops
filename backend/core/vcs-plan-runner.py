"""VCS plan lifecycle manager — speculative plans for PR events (Phase 4).

Provides:
  VCSPlanRunner.trigger_plan         — create VCSPlanRun, clone repo, run plan async
  VCSPlanRunner.cancel_stale_plans   — cancel in-progress plans for same PR
  VCSPlanRunner.get_pr_plans         — list all plan runs for a PR
  VCSPlanRunner.post_commit_status   — update GitHub commit status check
  VCSPlanRunner.post_or_update_comment — post/update PR comment via GitHub App

Depends on: github-app-client.py, vcs-plan-runner-helpers.py, terraform-runner.py
"""
from __future__ import annotations

import asyncio
import importlib.util as _ilu
import logging
import sys as _sys
import tempfile
from pathlib import Path
from typing import Any

from backend.db.database import get_session

logger = logging.getLogger(__name__)
_CORE_DIR = Path(__file__).resolve().parent
_POWEROPS_BASE_URL = "https://powerops.example.com"


def _load_core(filename: str, alias: str) -> Any:
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _CORE_DIR / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _gh():
    return _load_core("github-app-client.py", "github_app_client")

def _helpers():
    return _load_core("vcs-plan-runner-helpers.py", "vcs_plan_runner_helpers")

def _runner():
    return _load_core("terraform-runner.py", "terraform_runner")


class VCSPlanRunner:
    """Manages speculative plan lifecycle for PR events."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def trigger_plan(
        self,
        vcs_connection_id: str,
        workspace_id: str,
        workspace_name: str,
        repo_full_name: str,
        working_directory: str,
        installation_id: int,
        pr_number: int,
        commit_sha: str,
        branch: str,
    ) -> dict:
        """Create a VCSPlanRun record and schedule the plan in the background."""
        run = await self._create_run_record(
            vcs_connection_id=vcs_connection_id,
            workspace_id=workspace_id,
            pr_number=pr_number,
            commit_sha=commit_sha,
            branch=branch,
        )
        asyncio.create_task(self._execute_plan(
            run_id=run["id"],
            repo_full_name=repo_full_name,
            working_directory=working_directory,
            installation_id=installation_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            pr_number=pr_number,
            commit_sha=commit_sha,
            branch=branch,
        ))
        return run

    async def cancel_stale_plans(self, vcs_connection_id: str, pr_number: int) -> int:
        """Cancel all in-progress plans for a PR. Returns count cancelled."""
        from sqlalchemy import select, update
        from backend.db.models import VCSPlanRun
        async with get_session() as session:
            stmt = (
                update(VCSPlanRun)
                .where(
                    VCSPlanRun.vcs_connection_id == vcs_connection_id,
                    VCSPlanRun.pr_number == pr_number,
                    VCSPlanRun.status.in_(["pending", "running"]),
                )
                .values(status="cancelled")
                .returning(VCSPlanRun.id)
            )
            result = await session.execute(stmt)
            cancelled = result.fetchall()
            logger.info("Cancelled %d stale plans for PR #%d", len(cancelled), pr_number)
            return len(cancelled)

    async def get_pr_plans(self, vcs_connection_id: str, pr_number: int) -> list[dict]:
        """Return all plan runs for a given PR, newest first."""
        from sqlalchemy import select
        from backend.db.models import VCSPlanRun
        async with get_session() as session:
            stmt = (
                select(VCSPlanRun)
                .where(
                    VCSPlanRun.vcs_connection_id == vcs_connection_id,
                    VCSPlanRun.pr_number == pr_number,
                )
                .order_by(VCSPlanRun.triggered_at.desc())
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [self._run_to_dict(r) for r in rows]

    async def post_commit_status(
        self,
        repo: str,
        commit_sha: str,
        state: str,
        description: str,
        workspace_id: str,
        installation_id: int,
    ) -> None:
        """Update GitHub commit status check for a plan run."""
        gh = _gh()
        token = await gh.get_installation_token(installation_id)
        target_url = f"{_POWEROPS_BASE_URL}/workspaces/{workspace_id}"
        await gh.update_check_status(
            repo=repo, sha=commit_sha, state=state,
            description=description, target_url=target_url, token=token,
        )

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    async def _execute_plan(
        self,
        run_id: str,
        repo_full_name: str,
        working_directory: str,
        installation_id: int,
        workspace_id: str,
        workspace_name: str,
        pr_number: int,
        commit_sha: str,
        branch: str,
    ) -> None:
        gh = _gh()
        h = _helpers()
        token = await gh.get_installation_token(installation_id)
        status, plan_output, policy_passed = "failed", "", None

        await self._update_run_status(run_id, "running")
        await self.post_commit_status(
            repo_full_name, commit_sha, "pending",
            "TerraBot plan in progress...", workspace_id, installation_id,
        )

        try:
            with tempfile.TemporaryDirectory(prefix="terrabot-vcs-plan-") as tmp:
                clone_dir = gh.clone_repo(repo_full_name, commit_sha, tmp, token)
                tf = _runner().TerraformRunner(work_dir=str(clone_dir / working_directory))
                await tf.init()
                plan_result = await tf.plan()
                plan_output = getattr(plan_result, "raw_output", str(plan_result))
                status = "completed"
        except Exception as exc:
            logger.exception("VCS plan failed for %s#%d@%s", repo_full_name, pr_number, commit_sha[:8])
            plan_output = f"Plan failed:\n{exc}"

        summary_json = h.build_plan_summary_json(plan_output)
        comment_id = await self._post_plan_comment(
            gh=gh,
            repo=repo_full_name,
            pr_number=pr_number,
            commit_sha=commit_sha,
            branch=branch,
            workspace_name=workspace_name,
            workspace_id=workspace_id,
            plan_output=plan_output,
            status=status,
            policy_passed=policy_passed,
            token=token,
        )
        await self._update_run_completed(
            run_id=run_id, status=status,
            plan_output=plan_output, summary_json=summary_json,
            policy_passed=policy_passed, comment_id=comment_id,
        )
        gh_state = "success" if status == "completed" else "failure"
        desc = "TerraBot plan passed" if status == "completed" else "TerraBot plan failed"
        await self.post_commit_status(repo_full_name, commit_sha, gh_state, desc, workspace_id, installation_id)

    async def _post_plan_comment(
        self, *, gh: Any, repo: str, pr_number: int, commit_sha: str,
        branch: str, workspace_name: str, workspace_id: str,
        plan_output: str, status: str, policy_passed: bool | None, token: str,
    ) -> int | None:
        h = _helpers()
        body = h.format_pr_comment_body(
            commit_sha=commit_sha, branch=branch, workspace_name=workspace_name,
            plan_output=plan_output, status=status,
            powerops_url=f"{_POWEROPS_BASE_URL}/workspaces/{workspace_id}",
            policy_passed=policy_passed,
        )
        try:
            await gh.post_pr_comment(repo, pr_number, body, token)
        except Exception:
            logger.exception("Failed to post plan comment on %s#%d", repo, pr_number)
        return None  # comment_id resolved from GitHub response in real integration

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _create_run_record(self, **kwargs: Any) -> dict:
        from backend.db.models import VCSPlanRun
        async with get_session() as session:
            run = VCSPlanRun(**kwargs, status="pending")
            session.add(run)
            await session.flush()
            await session.refresh(run)
            return self._run_to_dict(run)

    async def _update_run_status(self, run_id: str, status: str) -> None:
        from backend.db.models import VCSPlanRun
        async with get_session() as session:
            run = await session.get(VCSPlanRun, run_id)
            if run:
                run.status = status

    async def _update_run_completed(
        self, run_id: str, status: str, plan_output: str,
        summary_json: str, policy_passed: bool | None, comment_id: int | None,
    ) -> None:
        from datetime import datetime, timezone
        from backend.db.models import VCSPlanRun
        async with get_session() as session:
            run = await session.get(VCSPlanRun, run_id)
            if run:
                run.status = status
                run.plan_output = plan_output
                run.plan_summary_json = summary_json
                run.policy_passed = policy_passed
                run.comment_id = comment_id
                run.completed_at = datetime.now(timezone.utc)

    def _run_to_dict(self, run: Any) -> dict:
        return {
            "id": run.id,
            "vcs_connection_id": run.vcs_connection_id,
            "workspace_id": run.workspace_id,
            "pr_number": run.pr_number,
            "commit_sha": run.commit_sha,
            "branch": run.branch,
            "status": run.status,
            "plan_output": run.plan_output,
            "plan_summary_json": run.plan_summary_json,
            "policy_passed": run.policy_passed,
            "comment_id": run.comment_id,
            "job_id": run.job_id,
            "triggered_at": run.triggered_at,
            "completed_at": run.completed_at,
        }
