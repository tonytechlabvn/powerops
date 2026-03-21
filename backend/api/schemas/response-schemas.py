"""API response Pydantic models.

Wraps core models for consistent HTTP response shapes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.core.models import (
    ApplyResult,
    CostEstimate,
    DestroyResult,
    InitResult,
    PlanResult,
    ResourceChange,
    Template,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Generic envelope
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    code: str = ""


class OkResponse(BaseModel):
    ok: bool = True
    message: str = ""


# ---------------------------------------------------------------------------
# Job responses
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    workspace_dir: str
    created_at: datetime
    completed_at: datetime | None = None
    output: str = ""
    error: str = ""


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


# ---------------------------------------------------------------------------
# Terraform operation responses
# ---------------------------------------------------------------------------


class InitResponse(BaseModel):
    job_id: str
    result: InitResult | None = None


class PlanResponse(BaseModel):
    job_id: str
    approval_id: str = ""
    result: PlanResult | None = None


class ApplyResponse(BaseModel):
    job_id: str
    result: ApplyResult | None = None


class DestroyResponse(BaseModel):
    job_id: str
    result: DestroyResult | None = None


class StateResponse(BaseModel):
    workspace: str
    state: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Template responses
# ---------------------------------------------------------------------------


class TemplateListResponse(BaseModel):
    templates: list[Template]
    total: int


class RenderResponse(BaseModel):
    name: str
    hcl: str
    variables_applied: dict[str, Any] = Field(default_factory=dict)


class ValidateResponse(BaseModel):
    result: ValidationResult


# ---------------------------------------------------------------------------
# Approval responses
# ---------------------------------------------------------------------------


class ApprovalResponse(BaseModel):
    id: str
    job_id: str
    workspace: str
    status: str  # pending | approved | rejected
    plan_summary: list[ResourceChange] = Field(default_factory=list)
    cost_estimate: CostEstimate | None = None
    created_at: datetime
    decided_at: datetime | None = None
    decided_by: str = ""
    reason: str = ""


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalResponse]
    total: int


# ---------------------------------------------------------------------------
# Config responses
# ---------------------------------------------------------------------------


class ProviderConfigResponse(BaseModel):
    provider: str
    configured: bool
    credentials_redacted: dict[str, str] = Field(
        default_factory=dict,
        description="Credential keys with values masked as '***'",
    )


# ---------------------------------------------------------------------------
# Health response
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str  # ok | degraded
    database: str  # connected | error
    terraform: str  # available | not_found
    version: str = "0.1.0"
