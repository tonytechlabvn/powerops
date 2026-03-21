"""Job lifecycle service.

Manages CRUD operations and status transitions for Job ORM records.
All methods operate within an injected AsyncSession for transactional safety.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Job as JobORM
from backend.core.models import Job, JobStatus, JobType


def _orm_to_pydantic(orm: JobORM) -> Job:
    """Convert ORM Job row to Pydantic Job model."""
    return Job(
        id=orm.id,
        type=JobType(orm.type),
        status=JobStatus(orm.status),
        workspace_dir=orm.workspace_dir,
        created_at=orm.created_at,
        completed_at=orm.completed_at,
        output=orm.output,
        error=orm.error,
    )


class JobService:
    """Manage Job records through their lifecycle.

    Args:
        session: Active async SQLAlchemy session (injected per-request).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, type: JobType, workspace: str) -> Job:
        """Create a new job in pending state."""
        orm = JobORM(
            id=str(uuid.uuid4()),
            type=type.value,
            status=JobStatus.pending.value,
            workspace_dir=workspace,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _orm_to_pydantic(orm)

    async def start_job(self, job_id: str) -> Job:
        """Transition job to running state."""
        orm = await self._get_orm(job_id)
        orm.status = JobStatus.running.value
        await self._session.flush()
        return _orm_to_pydantic(orm)

    async def complete_job(self, job_id: str, output: str = "") -> Job:
        """Transition job to completed state with captured output."""
        orm = await self._get_orm(job_id)
        orm.status = JobStatus.completed.value
        orm.output = output
        orm.completed_at = datetime.utcnow()
        await self._session.flush()
        return _orm_to_pydantic(orm)

    async def fail_job(self, job_id: str, error: str = "") -> Job:
        """Transition job to failed state with error message."""
        orm = await self._get_orm(job_id)
        orm.status = JobStatus.failed.value
        orm.error = error
        orm.completed_at = datetime.utcnow()
        await self._session.flush()
        return _orm_to_pydantic(orm)

    async def cancel_job(self, job_id: str) -> Job:
        """Transition job to cancelled state."""
        orm = await self._get_orm(job_id)
        orm.status = JobStatus.cancelled.value
        orm.completed_at = datetime.utcnow()
        await self._session.flush()
        return _orm_to_pydantic(orm)

    async def get_job(self, job_id: str) -> Job | None:
        """Return job by ID or None if not found."""
        stmt = select(JobORM).where(JobORM.id == job_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _orm_to_pydantic(orm) if orm else None

    async def list_jobs(
        self,
        workspace: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Job]:
        """Return jobs filtered by optional workspace and/or status."""
        stmt = select(JobORM).order_by(JobORM.created_at.desc()).limit(limit)
        if workspace:
            stmt = stmt.where(JobORM.workspace_dir.contains(workspace))
        if status:
            stmt = stmt.where(JobORM.status == status)
        result = await self._session.execute(stmt)
        rows: Sequence[JobORM] = result.scalars().all()
        return [_orm_to_pydantic(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_orm(self, job_id: str) -> JobORM:
        """Fetch ORM row by ID; raise ValueError if missing."""
        stmt = select(JobORM).where(JobORM.id == job_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise ValueError(f"Job not found: {job_id}")
        return orm
