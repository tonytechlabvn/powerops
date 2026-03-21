"""Approval queue routes.

GET  /api/approvals              — list all approvals
POST /api/approvals/{id}/decide  — approve or reject; auto-triggers apply on approve
"""
from __future__ import annotations

import sys

from fastapi import APIRouter, BackgroundTasks

from backend.core import get_settings, terraform_runner
from backend.core.models import JobType
from backend.api.schemas.request_schemas import ApprovalDecisionRequest
from backend.api.schemas.response_schemas import ApprovalListResponse, ApprovalResponse
from backend.db.database import get_session
from backend.api.services.approval_service import ApprovalService
from backend.api.services.job_service import JobService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _get_stream_service():
    return sys.modules["backend.api.services.stream_service"]


def _extract_errors_from_stream(lines: list[str]) -> list[str]:
    """Parse streamed Terraform JSON lines for error diagnostics."""
    import json
    errors: list[str] = []
    for line in lines:
        try:
            obj = json.loads(line)
            if obj.get("@level") == "error":
                msg = obj.get("@message", "")
                diag = obj.get("diagnostic", {})
                summary = diag.get("summary", "")
                errors.append(summary or msg or "Unknown error")
        except (json.JSONDecodeError, AttributeError):
            continue
    return errors


async def _run_apply_after_approval(job_id: str, workspace: str) -> None:
    """Background task: run terraform apply after approval."""
    from pathlib import Path
    ss = _get_stream_service()
    settings = get_settings()
    base = Path(settings.working_dir).resolve()
    ws_path = (base / workspace).resolve()

    try:
        ss.append_line(job_id, "[apply] Starting terraform apply...")
        runner = terraform_runner.TerraformRunner(
            working_dir=ws_path,
            binary=settings.terraform_binary,
            timeout=settings.op_timeout_seconds,
        )

        # Stream apply output
        buffered: list[str] = []
        async for line in runner.stream("apply", "-json", "-no-color", "-auto-approve"):
            ss.append_line(job_id, line)
            buffered.append(line)

        # Check for errors in the streamed output
        errors = _extract_errors_from_stream(buffered)
        if errors:
            error_msg = "; ".join(errors)
            async with get_session() as session:
                await JobService(session).fail_job(job_id, error=error_msg)
            ss.append_line(job_id, f"[error] Apply failed: {error_msg}")
            return

        # Get outputs (IP addresses, DNS names, etc.)
        outputs: dict = {}
        try:
            outputs = await runner.output()
        except Exception:
            pass

        output_text = "\n".join(buffered)
        if outputs:
            output_text += "\n\n--- OUTPUTS ---\n"
            for k, v in outputs.items():
                val = v.get("value", v) if isinstance(v, dict) else v
                output_text += f"{k} = {val}\n"
            ss.append_line(job_id, "--- DEPLOYMENT OUTPUTS ---")
            for k, v in outputs.items():
                val = v.get("value", v) if isinstance(v, dict) else v
                ss.append_line(job_id, f"  {k} = {val}")

        async with get_session() as session:
            await JobService(session).complete_job(job_id, output=output_text)

        ss.append_line(job_id, "[apply] Deployment completed successfully!")

    except Exception as exc:
        error_msg = str(exc)
        if hasattr(exc, "stderr") and exc.stderr:
            error_msg += f": {exc.stderr}"
        async with get_session() as session:
            await JobService(session).fail_job(job_id, error=error_msg)
        ss.append_line(job_id, f"[error] Apply failed: {error_msg}")


@router.get("", response_model=ApprovalListResponse)
async def list_approvals() -> ApprovalListResponse:
    """Return all approvals."""
    async with get_session() as session:
        svc = ApprovalService(session)
        approvals = await svc.list_pending()
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    background_tasks: BackgroundTasks,
) -> ApprovalResponse:
    """Approve or reject. On approve, auto-triggers terraform apply."""
    async with get_session() as session:
        svc = ApprovalService(session)
        approval = await svc.decide(
            approval_id,
            approved=body.approved,
            reason=body.reason,
        )
        workspace = approval.workspace

        # If approved, create apply job and run it
        if body.approved and workspace:
            job_svc = JobService(session)
            apply_job = await job_svc.create_job(JobType.apply, workspace)
            await job_svc.start_job(apply_job.id)
            background_tasks.add_task(
                _run_apply_after_approval, apply_job.id, workspace
            )

    return approval
