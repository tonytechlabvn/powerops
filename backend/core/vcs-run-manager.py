"""VCS-triggered run orchestration (Phase 3).

Handles GitHub webhook events and translates them into TerraBot job runs:
  - PR opened/synchronize  → speculative plan (posted back as PR comment + status)
  - PR closed + merged     → full plan (+ auto-apply if configured)
  - Push to tracked branch → full plan (+ auto-apply if configured)

Concurrency is capped by an asyncio.Semaphore seeded from settings.vcs_max_concurrent_runs.
DB helpers and plan formatting live in vcs-run-helpers.py.
"""
from __future__ import annotations

import asyncio
import importlib.util as _ilu
import logging
import sys as _sys
import tempfile
from pathlib import Path
from typing import Any

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

_CORE_DIR = Path(__file__).resolve().parent
_semaphore: asyncio.Semaphore | None = None


# ---------------------------------------------------------------------------
# Concurrency guard
# ---------------------------------------------------------------------------

def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(get_settings().vcs_max_concurrent_runs)
    return _semaphore


# ---------------------------------------------------------------------------
# Kebab-case sibling loader
# ---------------------------------------------------------------------------

def _load_core(filename: str, alias: str):
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

def _runner():
    return _load_core("terraform-runner.py", "terraform_runner")

def _helpers():
    return _load_core("vcs-run-helpers.py", "vcs_run_helpers")


# ---------------------------------------------------------------------------
# Public event handlers (called from webhook-routes.py)
# ---------------------------------------------------------------------------

async def handle_pr_event(action: str, pr_data: dict, repo: str, installation_id: int) -> None:
    """Route PR webhook actions to the appropriate run type."""
    h = _helpers()
    if action in ("opened", "synchronize", "reopened"):
        workspace, vcs_conn = await h.find_vcs_conn_by_repo(repo)
        if not workspace:
            logger.info("No VCS connection for repo %s — ignoring PR event", repo)
            return
        asyncio.create_task(_guarded(
            run_speculative_plan,
            workspace, vcs_conn,
            pr_data["head"]["sha"], pr_data["number"], installation_id,
        ))

    elif action == "closed" and pr_data.get("merged"):
        workspace, vcs_conn = await h.find_vcs_conn_by_repo(repo)
        if not workspace:
            return
        sha = pr_data.get("merge_commit_sha") or pr_data["head"]["sha"]
        asyncio.create_task(_guarded(run_full_plan, workspace, vcs_conn, sha, installation_id))


async def handle_push_event(ref: str, commits: list, repo: str, installation_id: int) -> None:
    """Handle push webhook: find matching VCS connection and trigger full plan."""
    if not ref.startswith("refs/heads/"):
        logger.debug("Ignoring non-branch push ref: %s", ref)
        return
    branch = ref[len("refs/heads/"):]

    h = _helpers()
    workspace, vcs_conn = await h.find_vcs_conn_by_repo_and_branch(repo, branch)
    if not workspace:
        logger.info("No VCS connection for %s@%s — ignoring push", repo, branch)
        return

    sha = commits[-1].get("id", "") if commits else ""
    asyncio.create_task(_guarded(run_full_plan, workspace, vcs_conn, sha, installation_id))


# ---------------------------------------------------------------------------
# Run implementations
# ---------------------------------------------------------------------------

async def run_speculative_plan(
    workspace: Any, vcs_conn: Any, commit_sha: str, pr_number: int, installation_id: int,
) -> None:
    """Clone repo, run terraform plan, post result as PR comment + commit status."""
    gh = _gh()
    h = _helpers()
    token = await gh.get_installation_token(installation_id)
    repo = vcs_conn.repo_full_name
    powerops_url = f"https://powerops.example.com/workspaces/{workspace.id}"

    await gh.update_check_status(repo=repo, sha=commit_sha, state="pending",
                                  description="TerraBot plan in progress...",
                                  target_url=powerops_url, token=token)

    final_state, plan_md, job_status = "failure", "", "failed"

    with tempfile.TemporaryDirectory(prefix="terrabot-vcs-") as tmp:
        try:
            clone_dir = gh.clone_repo(repo, commit_sha, tmp, token)
            tf = _runner().TerraformRunner(work_dir=str(clone_dir / vcs_conn.working_directory))
            await tf.init()
            plan_md = h.format_plan_summary(await tf.plan())
            final_state, job_status = "success", "completed"
        except Exception as exc:
            logger.exception("Speculative plan failed for %s#%s", repo, pr_number)
            plan_md = f"**Plan failed**\n```\n{exc}\n```"

    try:
        body = f"## TerraBot Plan — `{commit_sha[:8]}`\n\n{plan_md}\n\n[View in PowerOps]({powerops_url})"
        await gh.post_pr_comment(repo, pr_number, body, token)
    except Exception:
        logger.exception("Failed to post PR comment on %s#%s", repo, pr_number)

    desc = "TerraBot plan completed" if final_state == "success" else "TerraBot plan failed"
    await gh.update_check_status(repo=repo, sha=commit_sha, state=final_state,
                                  description=desc, target_url=powerops_url, token=token)

    await h.create_job_record(job_type="plan", status=job_status,
                               workspace_dir=vcs_conn.working_directory,
                               commit_sha=commit_sha, pr_number=pr_number,
                               trigger="vcs_pr", output=plan_md)


async def run_full_plan(
    workspace: Any, vcs_conn: Any, commit_sha: str, installation_id: int,
) -> None:
    """Clone repo, run plan (and optionally apply), create Approval if not auto-apply."""
    gh = _gh()
    h = _helpers()
    token = await gh.get_installation_token(installation_id)
    repo = vcs_conn.repo_full_name
    plan_md, job_status = "", "failed"

    with tempfile.TemporaryDirectory(prefix="terrabot-vcs-full-") as tmp:
        try:
            clone_dir = gh.clone_repo(repo, commit_sha, tmp, token)
            tf = _runner().TerraformRunner(work_dir=str(clone_dir / vcs_conn.working_directory))
            await tf.init()
            plan_md = h.format_plan_summary(await tf.plan())

            if vcs_conn.auto_apply:
                await tf.apply(auto_approve=True)
                job_status = "completed"
            else:
                await h.create_approval_record(workspace.name, plan_md)
                job_status = "awaiting_approval"

        except Exception as exc:
            logger.exception("Full plan failed for %s@%s", repo, commit_sha[:8])
            plan_md = str(exc)

    await h.create_job_record(job_type="plan", status=job_status,
                               workspace_dir=vcs_conn.working_directory,
                               commit_sha=commit_sha, pr_number=None,
                               trigger="vcs_push", output=plan_md)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _guarded(coro_fn, *args) -> None:
    """Execute a VCS run coroutine under the concurrency semaphore."""
    async with _get_semaphore():
        try:
            await coro_fn(*args)
        except Exception:
            logger.exception("VCS run failed in %s", coro_fn.__name__)
