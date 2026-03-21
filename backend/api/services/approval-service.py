"""Approval queue service.

Manages plan approval records using the Approval ORM model.
Approvals are created automatically when a plan job completes.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Approval as ApprovalORM
from backend.core.models import PlanResult, ResourceChange

if TYPE_CHECKING:
    from backend.api.schemas.response_schemas import ApprovalResponse


def _response_cls():
    """Lazy import of ApprovalResponse — avoids circular load at module init."""
    return sys.modules["backend.api.schemas.response_schemas"].ApprovalResponse


def _orm_to_response(orm: ApprovalORM):
    """Convert ORM Approval row to ApprovalResponse schema."""
    plan_summary: list[ResourceChange] = []
    if orm.plan_summary_json:
        try:
            raw = json.loads(orm.plan_summary_json)
            plan_summary = [ResourceChange(**r) for r in raw]
        except Exception:
            pass

    return _response_cls()(
        id=orm.id,
        job_id=orm.job_id,
        workspace=orm.workspace,
        status=orm.status,
        plan_summary=plan_summary,
        cost_estimate=None,
        created_at=orm.created_at,
        decided_at=orm.decided_at,
        decided_by=orm.decided_by,
        reason=orm.reason,
    )


class ApprovalService:
    """Manage plan approval records through their lifecycle.

    Args:
        session: Active async SQLAlchemy session (injected per-request).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_approval(
        self,
        job_id: str,
        workspace: str,
        plan_result: PlanResult,
    ):
        """Create a pending approval entry after a plan completes."""
        changes = [rc.model_dump() for rc in plan_result.resource_changes]
        orm = ApprovalORM(
            id=str(uuid.uuid4()),
            job_id=job_id,
            workspace=workspace,
            status="pending",
            plan_summary_json=json.dumps(changes),
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _orm_to_response(orm)

    async def get_approval(self, approval_id: str):
        """Return approval by ID or None if not found."""
        orm = await self._get_orm(approval_id)
        return _orm_to_response(orm) if orm else None

    async def get_approval_for_job(self, job_id: str):
        """Return the most recent approval for a given job."""
        stmt = (
            select(ApprovalORM)
            .where(ApprovalORM.job_id == job_id)
            .order_by(ApprovalORM.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _orm_to_response(orm) if orm else None

    async def list_pending(self) -> list:
        """Return all approvals with status='pending'."""
        stmt = (
            select(ApprovalORM)
            .where(ApprovalORM.status == "pending")
            .order_by(ApprovalORM.created_at.asc())
        )
        result = await self._session.execute(stmt)
        rows: Sequence[ApprovalORM] = result.scalars().all()
        return [_orm_to_response(r) for r in rows]

    async def decide(
        self,
        approval_id: str,
        approved: bool,
        reason: str = "",
        decided_by: str = "system",
    ):
        """Record an approve/reject decision on a pending approval."""
        orm = await self._get_orm(approval_id)
        if orm is None:
            raise ValueError(f"Approval not found: {approval_id}")
        if orm.status != "pending":
            raise ValueError(f"Approval {approval_id} is already '{orm.status}'")
        orm.status = "approved" if approved else "rejected"
        orm.decided_at = datetime.utcnow()
        orm.decided_by = decided_by
        orm.reason = reason
        await self._session.flush()
        return _orm_to_response(orm)

    async def _get_orm(self, approval_id: str) -> ApprovalORM | None:
        stmt = select(ApprovalORM).where(ApprovalORM.id == approval_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
