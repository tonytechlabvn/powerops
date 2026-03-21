"""Job management routes.

GET    /api/jobs                — list jobs with optional filters
GET    /api/jobs/{job_id}       — job details
DELETE /api/jobs/{job_id}       — cancel a pending or running job
PATCH  /api/jobs/{job_id}/hide  — soft-delete a terminal job
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.core.models import JobStatus
from backend.api.schemas.response_schemas import JobListResponse, JobResponse
from backend.db.database import get_session
from backend.api.services.job_service import JobService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_to_response(job) -> JobResponse:
    return JobResponse(
        id=job.id,
        type=job.type.value if hasattr(job.type, "value") else str(job.type),
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        workspace_dir=job.workspace_dir,
        created_at=job.created_at,
        completed_at=job.completed_at,
        output=job.output,
        error=job.error,
        is_hidden=job.is_hidden,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    workspace: str | None = Query(None, description="Filter by workspace name"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    include_hidden: bool = Query(False, description="Include hidden (soft-deleted) jobs"),
) -> JobListResponse:
    """List jobs with optional workspace and status filters."""
    async with get_session() as session:
        svc = JobService(session)
        jobs = await svc.list_jobs(
            workspace=workspace, status=status, limit=limit,
            include_hidden=include_hidden,
        )
    return JobListResponse(jobs=[_job_to_response(j) for j in jobs], total=len(jobs))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Return a single job by ID."""
    async with get_session() as session:
        job = await JobService(session).get_job(job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")
    return _job_to_response(job)


@router.delete("/{job_id}", response_model=JobResponse)
async def cancel_job(job_id: str) -> JobResponse:
    """Cancel a job that is pending or running."""
    async with get_session() as session:
        svc = JobService(session)
        job = await svc.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        if job.status not in (JobStatus.pending, JobStatus.running):
            raise ValueError(
                f"Job {job_id} is already '{job.status.value}' and cannot be cancelled"
            )
        job = await svc.cancel_job(job_id)
    return _job_to_response(job)


@router.patch("/{job_id}/hide", response_model=JobResponse)
async def hide_job(job_id: str) -> JobResponse:
    """Soft-delete a terminal job (completed/failed/cancelled)."""
    async with get_session() as session:
        svc = JobService(session)
        job = await svc.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        terminal = (JobStatus.completed, JobStatus.failed, JobStatus.cancelled)
        if job.status not in terminal:
            raise ValueError(
                f"Only terminal jobs can be hidden (current: '{job.status.value}')"
            )
        job = await svc.hide_job(job_id)
    return _job_to_response(job)
