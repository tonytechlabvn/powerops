"""API request Pydantic models.

All fields map to what the frontend/CLI sends to the REST API.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Terraform operation requests
# ---------------------------------------------------------------------------


class InitRequest(BaseModel):
    workspace: str = Field(..., description="Workspace name / directory key")
    provider: str = Field("", description="Provider name (aws | proxmox | azure)")
    upgrade: bool = Field(False, description="Pass -upgrade to terraform init")
    extra_env: dict[str, str] = Field(default_factory=dict, description="Extra env vars for TF")


class PlanRequest(BaseModel):
    workspace: str = Field(..., description="Workspace name / directory key")
    var_file: str | None = Field(None, description="Path to .tfvars file inside workspace")
    destroy: bool = Field(False, description="Run destroy plan instead of normal plan")
    extra_env: dict[str, str] = Field(default_factory=dict)


class ApplyRequest(BaseModel):
    workspace: str = Field(..., description="Workspace name / directory key")
    approval_id: str = Field(..., description="Approval ID from the pending approval queue")
    plan_file: str | None = Field(None, description="Saved plan binary path (relative to workspace)")
    extra_env: dict[str, str] = Field(default_factory=dict)


class DestroyRequest(BaseModel):
    workspace: str = Field(..., description="Workspace name / directory key")
    confirmation: str = Field(..., description='Must equal "destroy" to confirm')
    var_file: str | None = Field(None)
    extra_env: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Template requests
# ---------------------------------------------------------------------------


class RenderTemplateRequest(BaseModel):
    name: str = Field(..., description='Template identifier e.g. "aws/ec2-web-server"')
    variables: dict[str, Any] = Field(default_factory=dict)


class ValidateHCLRequest(BaseModel):
    hcl: str = Field(..., description="Raw HCL string to validate")


# ---------------------------------------------------------------------------
# Config requests
# ---------------------------------------------------------------------------


class ProviderConfigRequest(BaseModel):
    provider: str = Field(..., description="Provider name (aws | proxmox | azure | gcp)")
    credentials: dict[str, str] = Field(..., description="Provider-specific credential key/value pairs")


# ---------------------------------------------------------------------------
# Approval requests
# ---------------------------------------------------------------------------


class ApprovalDecisionRequest(BaseModel):
    approved: bool = Field(..., description="True = approve, False = reject")
    reason: str = Field("", description="Optional human-readable reason")
