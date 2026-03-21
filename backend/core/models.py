"""Pydantic schemas for all TerraBot data exchange.

These models are used by both the CLI and FastAPI layers.
They are independent of SQLAlchemy ORM models in db/models.py.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JobType(str, Enum):
    init = "init"
    plan = "plan"
    apply = "apply"
    destroy = "destroy"
    validate = "validate"
    output = "output"
    show = "show"


class ChangeAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    replace = "replace"
    no_op = "no-op"
    read = "read"


# ---------------------------------------------------------------------------
# Terraform runner results
# ---------------------------------------------------------------------------


class ResourceChange(BaseModel):
    address: str
    type: str
    name: str
    action: ChangeAction
    provider: str = ""


class PlanResult(BaseModel):
    success: bool
    format_version: str = ""
    terraform_version: str = ""
    resource_changes: list[ResourceChange] = Field(default_factory=list)
    resource_drift: list[ResourceChange] = Field(default_factory=list)
    raw_output: str = ""
    stderr: str = ""
    plan_file: str = ""  # path to saved plan binary


class ApplyResult(BaseModel):
    success: bool
    resource_changes: list[ResourceChange] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
    raw_output: str = ""
    stderr: str = ""


class DestroyResult(BaseModel):
    success: bool
    resources_destroyed: int = 0
    raw_output: str = ""
    stderr: str = ""


class InitResult(BaseModel):
    success: bool
    raw_output: str = ""
    stderr: str = ""


class ShowResult(BaseModel):
    success: bool
    state: dict[str, Any] = Field(default_factory=dict)
    raw_output: str = ""


# ---------------------------------------------------------------------------
# Job tracking
# ---------------------------------------------------------------------------


class Job(BaseModel):
    id: str
    type: JobType
    status: JobStatus = JobStatus.pending
    workspace_dir: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    output: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# HCL validation
# ---------------------------------------------------------------------------


class Resource(BaseModel):
    type: str
    name: str
    address: str = ""  # e.g. "aws_instance.web"
    attributes: dict[str, Any] = Field(default_factory=dict)


class Violation(BaseModel):
    resource_type: str
    resource_name: str
    reason: str


class ValidationResult(BaseModel):
    valid: bool
    violations: list[Violation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TemplateVariable(BaseModel):
    name: str
    type: str = "string"  # string | number | bool | list | map
    description: str = ""
    default: Any = None
    required: bool = True


class TemplateMetadata(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    provider: str = ""  # aws | proxmox | azure | gcp
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)
    author: str = ""


class Template(BaseModel):
    metadata: TemplateMetadata
    variables: list[TemplateVariable] = Field(default_factory=list)
    path: str = ""  # absolute path to template directory


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


class ResourceCost(BaseModel):
    resource_type: str
    resource_address: str
    monthly_usd: float
    notes: str = ""


class CostEstimate(BaseModel):
    total_monthly_usd: float
    breakdown: list[ResourceCost] = Field(default_factory=list)
    currency: str = "USD"
    disclaimer: str = "Estimates are approximate and may not reflect actual AWS pricing."


# ---------------------------------------------------------------------------
# AI agent results (Phase 5)
# ---------------------------------------------------------------------------


class GenerationResult(BaseModel):
    success: bool
    hcl: str = ""
    explanation: str = ""  # plain-English explanation of the generated HCL
    template_used: str = ""
    variables_applied: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class DiagnosisResult(BaseModel):
    success: bool
    root_cause: str = ""
    suggested_fixes: list[str] = Field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ReviewResult(BaseModel):
    success: bool
    approved: bool = False
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    security_concerns: list[str] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
