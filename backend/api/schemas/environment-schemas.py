"""Pydantic schemas for Environment and variable management endpoints (Phase 2).

Models:
  CreateEnvironmentRequest    — body for POST /api/environments
  UpdateEnvironmentRequest    — body for PATCH /api/environments/{id}
  EnvironmentResponse         — response for environment queries
  SetVariableRequest          — body for POST /api/environments/{id}/variables
  VariableResponse            — response for a single variable
  EffectiveVariableResponse   — merged env+workspace variable result
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateEnvironmentRequest(BaseModel):
    """Request body to create a new environment."""
    name: str = Field(..., min_length=1, max_length=64, description="Environment name (dev/staging/prod)")
    description: str = Field("", description="Optional description")
    org_id: str = Field(..., description="Organization ID this environment belongs to")
    color: str = Field("#6366f1", description="Hex color for UI badge")
    is_protected: bool = Field(False, description="Protected envs require admin to delete")
    auto_apply: bool = Field(False, description="Auto-apply plans in this environment")


class UpdateEnvironmentRequest(BaseModel):
    """Partial update for an existing environment."""
    name: str | None = Field(None, max_length=64)
    description: str | None = None
    color: str | None = None
    is_protected: bool | None = None
    auto_apply: bool | None = None


class EnvironmentResponse(BaseModel):
    """Response body for environment queries."""
    id: str
    name: str
    description: str
    org_id: str
    color: str
    is_protected: bool
    auto_apply: bool
    created_at: datetime
    variable_count: int = 0
    workspace_count: int = 0

    model_config = {"from_attributes": True}


class SetVariableRequest(BaseModel):
    """Request body to create or update a variable in an environment or workspace."""
    key: str = Field(..., min_length=1, max_length=256)
    value: str = Field("", description="Variable value; encrypted at rest if is_sensitive=True")
    is_sensitive: bool = Field(False, description="Mask value in API responses")
    is_hcl: bool = Field(False, description="Value is HCL expression, not a string literal")
    category: str = Field("terraform", description="'terraform' (TF_VAR_*) or 'env' (plain env var)")
    description: str = Field("", description="Human-readable description")


class VariableResponse(BaseModel):
    """Response body for a single variable (sensitive value masked)."""
    id: str
    key: str
    value: str          # "***" when is_sensitive=True
    is_sensitive: bool
    is_hcl: bool
    category: str
    description: str

    model_config = {"from_attributes": True}


class EffectiveVariableResponse(BaseModel):
    """Merged variable from environment+workspace inheritance chain."""
    key: str
    value: str
    is_sensitive: bool
    is_hcl: bool
    category: str
    source: str         # "environment" | "workspace"
    description: str
