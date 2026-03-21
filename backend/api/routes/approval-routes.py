"""Approval queue routes.

GET  /api/approvals              — list pending approvals
POST /api/approvals/{id}/decide  — approve or reject a pending plan
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas.request_schemas import ApprovalDecisionRequest
from backend.api.schemas.response_schemas import ApprovalListResponse, ApprovalResponse
from backend.db.database import get_session
from backend.api.services.approval_service import ApprovalService

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalListResponse)
async def list_pending_approvals() -> ApprovalListResponse:
    """Return all approvals currently awaiting a decision."""
    async with get_session() as session:
        svc = ApprovalService(session)
        approvals = await svc.list_pending()
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
) -> ApprovalResponse:
    """Approve or reject a pending plan approval."""
    async with get_session() as session:
        svc = ApprovalService(session)
        approval = await svc.decide(
            approval_id,
            approved=body.approved,
            reason=body.reason,
        )
    return approval
