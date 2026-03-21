"""Auto deploy route: one-click EC2 deployment with smart defaults.

POST /api/deploy/auto — auto-detect AMI, generate SSH key pair, deploy
"""
from __future__ import annotations

import os
import sys
import uuid

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from backend.core import get_settings
from backend.core.models import JobType
from backend.db.database import get_session
from backend.api.services.job_service import JobService

router = APIRouter(prefix="/api/deploy", tags=["auto-deploy"])


def _get_ami_resolver():
    """Lazy-load ami-resolver module (kebab-case filename)."""
    import importlib.util, pathlib
    name = "backend.core.ami_resolver"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, pathlib.Path(__file__).parents[2] / "core" / "ami-resolver.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _get_deploy_runner():
    """Lazy-load _run_deploy from deploy-routes module."""
    return sys.modules["backend.api.routes.deploy_routes"]


class AutoDeployRequest(BaseModel):
    instance_name: str = Field("auto-web-server", description="Name tag for the instance")
    instance_type: str = Field("t3.micro", description="EC2 instance type")
    os_type: str = Field("amazon-linux-2023", description="OS: amazon-linux-2023 or ubuntu-22.04")
    environment: str = Field("dev", description="Environment tag")


class AutoDeployResponse(BaseModel):
    job_id: str
    workspace: str
    stream_url: str


@router.post("/auto", response_model=AutoDeployResponse)
async def auto_deploy(
    body: AutoDeployRequest, background_tasks: BackgroundTasks
) -> AutoDeployResponse:
    """Auto-deploy EC2 with smart defaults: resolve AMI, generate key pair."""

    # Validate AWS credentials are configured
    region = os.environ.get("AWS_DEFAULT_REGION", "")
    if not region or not os.environ.get("AWS_ACCESS_KEY_ID"):
        raise ValueError(
            "AWS credentials not configured. Go to Config page to set them up."
        )

    # Resolve latest AMI for the region
    ami_resolver = _get_ami_resolver()
    ami_id = ami_resolver.resolve_ami(region, body.os_type)
    ssh_user = ami_resolver.get_ssh_user(body.os_type)

    # Build variables with smart defaults
    variables: dict = {
        "aws_region": region,
        "ami_id": ami_id,
        "instance_type": body.instance_type,
        "instance_name": body.instance_name,
        "key_name": f"{body.instance_name}-key",
        "auto_key_pair": True,
        "ssh_user": ssh_user,
        "allowed_ssh_cidr": "0.0.0.0/0",
        "root_volume_size_gb": 20,
        "environment": body.environment,
    }

    # Create job and reuse existing deploy pipeline
    template_name = "aws/ec2-web-server"
    workspace = f"{template_name.replace('/', '-')}-{uuid.uuid4().hex[:8]}"

    async with get_session() as session:
        svc = JobService(session)
        job = await svc.create_job(JobType.plan, workspace)
        await svc.start_job(job.id)

    deploy_mod = _get_deploy_runner()
    background_tasks.add_task(
        deploy_mod._run_deploy, job.id, workspace, template_name, variables
    )

    return AutoDeployResponse(
        job_id=job.id,
        workspace=workspace,
        stream_url=f"/api/stream/{job.id}",
    )
