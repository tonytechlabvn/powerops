"""Deploy route: one-click template → workspace → init → plan.

POST /api/deploy — render template into workspace, run init+plan, return job_id
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from backend.core import get_settings, template_engine, terraform_runner
from backend.core.models import JobType
from backend.db.database import get_session
from backend.api.services.job_service import JobService
from backend.api.services.approval_service import ApprovalService

router = APIRouter(prefix="/api", tags=["deploy"])


def _extract_plan_errors(lines: list[str]) -> list[str]:
    """Parse streamed Terraform JSON lines for error diagnostics."""
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


class DeployRequest(BaseModel):
    template: str = Field(..., description='Template name e.g. "aws/ec2-web-server"')
    variables: dict[str, Any] = Field(default_factory=dict)
    workspace: str = Field("", description="Workspace name (auto-generated if empty)")


class DeployResponse(BaseModel):
    job_id: str
    workspace: str
    stream_url: str


def _get_stream_service():
    return sys.modules["backend.api.services.stream_service"]


def _workspace_path(workspace: str) -> Path:
    settings = get_settings()
    base = Path(settings.working_dir).resolve()
    ws_path = (base / workspace).resolve()
    if not str(ws_path).startswith(str(base)):
        raise ValueError(f"Invalid workspace path: {workspace}")
    ws_path.mkdir(parents=True, exist_ok=True)
    return ws_path


async def _run_deploy(
    job_id: str, workspace: str, template_name: str, variables: dict[str, Any]
) -> None:
    """Background task: render template → write files → init → plan."""
    ss = _get_stream_service()
    settings = get_settings()
    ws_path = _workspace_path(workspace)

    try:
        # Step 1: Render template
        ss.append_line(job_id, f"[deploy] Rendering template: {template_name}")
        rendered_hcl = template_engine.render_template(template_name, variables)

        # Write rendered HCL to workspace
        main_tf = ws_path / "main.tf"
        main_tf.write_text(rendered_hcl, encoding="utf-8")
        ss.append_line(job_id, f"[deploy] Wrote {len(rendered_hcl)} bytes to {workspace}/main.tf")

        # Step 2: Terraform init
        ss.append_line(job_id, "[deploy] Running terraform init...")
        runner = terraform_runner.TerraformRunner(
            working_dir=ws_path,
            binary=settings.terraform_binary,
            timeout=settings.op_timeout_seconds,
        )
        await runner.init()
        ss.append_line(job_id, "[deploy] Init completed")

        # Step 3: Terraform plan (stream output)
        ss.append_line(job_id, "[deploy] Running terraform plan...")
        buffered_lines: list[str] = []
        async for line in runner.stream("plan", "-json", "-no-color"):
            ss.append_line(job_id, line)
            buffered_lines.append(line)

        # Check for errors in streamed plan output
        plan_errors = _extract_plan_errors(buffered_lines)
        if plan_errors:
            error_msg = "; ".join(plan_errors)
            async with get_session() as session:
                await JobService(session).fail_job(job_id, error=error_msg)
            ss.append_line(job_id, f"[error] Plan failed: {error_msg}")
            return

        # Get structured plan result for approval
        result = await runner.plan()
        output = "\n".join(buffered_lines)

        async with get_session() as session:
            await JobService(session).complete_job(job_id, output=output)
            await ApprovalService(session).create_approval(job_id, workspace, result)

        ss.append_line(job_id, "[deploy] Plan completed — review and approve to apply")

    except Exception as exc:
        # Include specific violations for ValidationError
        error_msg = str(exc)
        if hasattr(exc, "violations") and exc.violations:
            error_msg += ": " + "; ".join(exc.violations)
        async with get_session() as session:
            await JobService(session).fail_job(job_id, error=error_msg)
        ss.append_line(job_id, f"[error] {error_msg}")


@router.post("/deploy", response_model=DeployResponse)
async def deploy_template(
    body: DeployRequest, background_tasks: BackgroundTasks
) -> DeployResponse:
    """Render template into workspace, run init + plan as background job."""
    workspace = body.workspace.strip() or f"{body.template.replace('/', '-')}-{uuid.uuid4().hex[:8]}"

    async with get_session() as session:
        svc = JobService(session)
        job = await svc.create_job(JobType.plan, workspace)
        await svc.start_job(job.id)

    background_tasks.add_task(_run_deploy, job.id, workspace, body.template, body.variables)

    return DeployResponse(
        job_id=job.id,
        workspace=workspace,
        stream_url=f"/api/stream/{job.id}",
    )
