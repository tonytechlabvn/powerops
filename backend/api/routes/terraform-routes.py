"""Terraform operation routes.

POST /api/terraform/init          — initialise workspace
POST /api/terraform/plan          — create plan job (async, returns job_id)
POST /api/terraform/apply         — apply after approval
POST /api/terraform/destroy       — destroy after confirmation
GET  /api/terraform/state/{ws}    — current state summary for workspace
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks

from backend.core import get_settings, terraform_runner
from backend.core.models import JobType
from backend.api.schemas.request_schemas import (
    ApplyRequest,
    DestroyRequest,
    InitRequest,
    PlanRequest,
)
from backend.api.schemas.response_schemas import (
    ApplyResponse,
    DestroyResponse,
    InitResponse,
    PlanResponse,
    StateResponse,
)
from backend.db.database import get_session
from backend.api.services.job_service import JobService
from backend.api.services.approval_service import ApprovalService

router = APIRouter(prefix="/api/terraform", tags=["terraform"])


def _get_stream_service():
    """Lazy-resolve stream_service from sys.modules (loaded by main.py)."""
    return sys.modules["backend.api.services.stream_service"]


def _workspace_path(workspace: str) -> Path:
    """Resolve absolute workspace directory from the configured base."""
    settings = get_settings()
    base = Path(settings.working_dir).resolve()
    ws_path = (base / workspace).resolve()
    # Prevent path traversal outside working_dir
    if not str(ws_path).startswith(str(base)):
        raise ValueError(f"Invalid workspace path: {workspace}")
    ws_path.mkdir(parents=True, exist_ok=True)
    return ws_path


def _make_runner(workspace: str, extra_env: dict[str, str] | None = None):
    settings = get_settings()
    return terraform_runner.TerraformRunner(
        working_dir=_workspace_path(workspace),
        binary=settings.terraform_binary,
        timeout=settings.op_timeout_seconds,
        extra_env=extra_env or {},
    )


# ---------------------------------------------------------------------------
# Background task helpers — each runs as a FireAndForget coroutine
# ---------------------------------------------------------------------------


async def _run_init(job_id: str, workspace: str, upgrade: bool, extra_env: dict) -> None:
    ss = _get_stream_service()
    runner = _make_runner(workspace, extra_env)
    try:
        result = await runner.init(upgrade=upgrade)
        async with get_session() as session:
            await JobService(session).complete_job(job_id, output=result.raw_output)
        ss.append_line(job_id, "[init] completed successfully")
    except Exception as exc:
        async with get_session() as session:
            await JobService(session).fail_job(job_id, error=str(exc))
        ss.append_line(job_id, f"[error] {exc}")


async def _run_plan(
    job_id: str,
    workspace: str,
    var_file: str | None,
    destroy: bool,
    extra_env: dict,
) -> None:
    ss = _get_stream_service()
    runner = _make_runner(workspace, extra_env)
    try:
        # Stream raw lines into the SSE buffer
        stream_args = ["plan", "-json", "-no-color"]
        if var_file:
            stream_args.append(f"-var-file={var_file}")
        if destroy:
            stream_args.append("-destroy")

        buffered_lines: list[str] = []
        async for line in runner.stream(*stream_args):
            ss.append_line(job_id, line)
            buffered_lines.append(line)

        # Re-run structured plan for approval summary (uses saved state)
        result = await runner.plan(var_file=var_file, destroy=destroy)
        output = "\n".join(buffered_lines)

        async with get_session() as session:
            await JobService(session).complete_job(job_id, output=output)
            await ApprovalService(session).create_approval(job_id, workspace, result)

        ss.append_line(job_id, "[plan] completed — approval required before apply")
    except Exception as exc:
        async with get_session() as session:
            await JobService(session).fail_job(job_id, error=str(exc))
        ss.append_line(job_id, f"[error] {exc}")


def _extract_errors_from_stream(lines: list[str]) -> list[str]:
    """Parse streamed Terraform JSON lines for error diagnostics."""
    import json as _json
    errors: list[str] = []
    for line in lines:
        try:
            obj = _json.loads(line)
            if obj.get("@level") == "error":
                msg = obj.get("@message", "")
                diag = obj.get("diagnostic", {})
                summary = diag.get("summary", "")
                errors.append(summary or msg or "Unknown error")
        except (_json.JSONDecodeError, AttributeError):
            continue
    return errors


async def _run_apply(
    job_id: str,
    workspace: str,
    plan_file: str | None,
    extra_env: dict,
) -> None:
    ss = _get_stream_service()
    runner = _make_runner(workspace, extra_env)
    try:
        stream_args = ["apply", "-json", "-no-color", "-auto-approve"]
        if plan_file:
            stream_args.append(plan_file)

        buffered: list[str] = []
        async for line in runner.stream(*stream_args):
            ss.append_line(job_id, line)
            buffered.append(line)

        # Check for errors in the streamed output
        errors = _extract_errors_from_stream(buffered)
        if errors:
            error_msg = "; ".join(errors)
            async with get_session() as session:
                await JobService(session).fail_job(job_id, error=error_msg)
            ss.append_line(job_id, f"[error] {error_msg}")
            return

        output_text = "\n".join(buffered)
        async with get_session() as session:
            await JobService(session).complete_job(job_id, output=output_text)
        ss.append_line(job_id, "[apply] completed successfully")
    except Exception as exc:
        async with get_session() as session:
            await JobService(session).fail_job(job_id, error=str(exc))
        ss.append_line(job_id, f"[error] {exc}")


async def _run_destroy(
    job_id: str,
    workspace: str,
    var_file: str | None,
    extra_env: dict,
) -> None:
    ss = _get_stream_service()
    runner = _make_runner(workspace, extra_env)
    try:
        stream_args = ["destroy", "-json", "-no-color", "-auto-approve"]
        if var_file:
            stream_args.append(f"-var-file={var_file}")

        async for line in runner.stream(*stream_args):
            ss.append_line(job_id, line)

        result = await runner.destroy(auto_approve=True, var_file=var_file)
        async with get_session() as session:
            await JobService(session).complete_job(job_id, output=result.raw_output)
        ss.append_line(
            job_id,
            f"[destroy] completed — {result.resources_destroyed} resources destroyed",
        )
    except Exception as exc:
        async with get_session() as session:
            await JobService(session).fail_job(job_id, error=str(exc))
        ss.append_line(job_id, f"[error] {exc}")


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.post("/init", response_model=InitResponse)
async def terraform_init(
    body: InitRequest, background_tasks: BackgroundTasks
) -> InitResponse:
    """Initialise a workspace. Runs terraform init as a background job."""
    async with get_session() as session:
        svc = JobService(session)
        job = await svc.create_job(JobType.init, body.workspace)
        await svc.start_job(job.id)

    background_tasks.add_task(
        _run_init, job.id, body.workspace, body.upgrade, body.extra_env
    )
    return InitResponse(job_id=job.id)


@router.post("/plan", response_model=PlanResponse)
async def terraform_plan(
    body: PlanRequest, background_tasks: BackgroundTasks
) -> PlanResponse:
    """Create a plan job. Returns job_id; stream output via /api/stream/{job_id}."""
    async with get_session() as session:
        svc = JobService(session)
        job = await svc.create_job(JobType.plan, body.workspace)
        await svc.start_job(job.id)

    background_tasks.add_task(
        _run_plan, job.id, body.workspace, body.var_file, body.destroy, body.extra_env
    )
    return PlanResponse(job_id=job.id)


@router.post("/apply", response_model=ApplyResponse)
async def terraform_apply(
    body: ApplyRequest, background_tasks: BackgroundTasks
) -> ApplyResponse:
    """Apply after verifying approval_id is in approved state."""
    async with get_session() as session:
        approval_svc = ApprovalService(session)
        approval = await approval_svc.get_approval(body.approval_id)
        if approval is None:
            raise ValueError(f"Approval not found: {body.approval_id}")
        if approval.status != "approved":
            raise ValueError(
                f"Approval {body.approval_id} has status '{approval.status}'; "
                "must be 'approved' before apply"
            )
        svc = JobService(session)
        job = await svc.create_job(JobType.apply, body.workspace)
        await svc.start_job(job.id)

    background_tasks.add_task(
        _run_apply, job.id, body.workspace, body.plan_file, body.extra_env
    )
    return ApplyResponse(job_id=job.id)


@router.post("/destroy", response_model=DestroyResponse)
async def terraform_destroy(
    body: DestroyRequest, background_tasks: BackgroundTasks
) -> DestroyResponse:
    """Destroy workspace resources. Requires confirmation='destroy' in body."""
    if body.confirmation != "destroy":
        raise ValueError("confirmation field must equal 'destroy' to proceed")

    async with get_session() as session:
        svc = JobService(session)
        job = await svc.create_job(JobType.destroy, body.workspace)
        await svc.start_job(job.id)

    background_tasks.add_task(
        _run_destroy, job.id, body.workspace, body.var_file, body.extra_env
    )
    return DestroyResponse(job_id=job.id)


@router.get("/state/{workspace:path}", response_model=StateResponse)
async def get_state(workspace: str) -> StateResponse:
    """Return current Terraform state summary for a workspace."""
    runner = _make_runner(workspace)
    show_result = await runner.show()
    outputs: dict = {}
    try:
        outputs = await runner.output()
    except Exception:
        pass  # workspace may not have outputs defined yet
    return StateResponse(
        workspace=workspace,
        state=show_result.state,
        outputs=outputs,
    )
