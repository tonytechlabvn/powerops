"""Pydantic schemas for Policy as Code endpoints (Phase 4).

Models:
  PolicyCreateRequest       — body for POST /api/policies
  PolicyUpdateRequest       — body for PUT /api/policies/{id}
  PolicyResponse            — response for policy queries
  PolicyTestRequest         — body for POST /api/policies/{id}/test
  PolicyTestResponse        — response for policy test
  PolicySetCreateRequest    — body for POST /api/policy-sets
  PolicySetResponse         — response for policy set queries
  PolicySetAssignRequest    — body for POST /api/policy-sets/{id}/assign
  PolicyCheckResultResponse — response for policy check results
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    """Request body to create a new policy."""
    name: str = Field(..., description="Unique policy name (used as OPA module ID)")
    description: str = Field("", description="Human-readable description")
    rego_code: str = Field(..., description="Rego source code for this policy")
    enforcement: str = Field(
        "advisory",
        description="Enforcement level: advisory | soft-mandatory | hard-mandatory",
    )


class PolicyUpdateRequest(BaseModel):
    """Partial update for an existing policy."""
    name: str | None = Field(None, description="New policy name")
    description: str | None = Field(None, description="New description")
    rego_code: str | None = Field(None, description="Updated Rego source code")
    enforcement: str | None = Field(None, description="New enforcement level")


class PolicyResponse(BaseModel):
    """Response body for policy queries."""
    id: str
    name: str
    description: str
    enforcement: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyTestRequest(BaseModel):
    """Request body for testing a policy against a sample plan."""
    plan_json: dict[str, Any] = Field(..., description="Sample Terraform plan JSON")


class PolicyTestResponse(BaseModel):
    """Result of evaluating a policy against a test plan."""
    violations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    passed: bool


class PolicySetCreateRequest(BaseModel):
    """Request body to create a policy set."""
    name: str = Field(..., description="Unique policy set name")
    description: str = Field("", description="Human-readable description")
    scope: str = Field(
        "workspace",
        description="Scope: workspace (assigned per-workspace) | global (org-wide)",
    )


class PolicySetResponse(BaseModel):
    """Response body for policy set queries."""
    id: str
    name: str
    description: str
    scope: str
    policy_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicySetAssignRequest(BaseModel):
    """Request body to assign a policy set to one or more workspaces."""
    workspace_ids: list[str] = Field(..., description="List of workspace IDs to assign")


class PolicyCheckResultResponse(BaseModel):
    """Response body for a single policy check result."""
    id: str
    policy_name: str
    enforcement: str
    passed: bool
    violations: list[dict[str, Any]] = Field(default_factory=list)
    evaluated_at: datetime

    model_config = {"from_attributes": True}
