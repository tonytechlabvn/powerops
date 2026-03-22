"""Pydantic request/response schemas for HCP Terraform Cloud endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class TFCSetupRequest(BaseModel):
    """Store TFC connection config for a project."""

    org_name: str
    api_token: str

    @field_validator("org_name")
    @classmethod
    def org_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("org_name is required")
        return v

    @field_validator("api_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("api_token is required")
        return v


class TFCVariableRequest(BaseModel):
    """A single variable to push to a TFC workspace."""

    key: str
    value: str
    category: str = "terraform"  # terraform | env
    sensitive: bool = False
    description: str = ""
    hcl: bool = False

    @field_validator("category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        if v not in {"terraform", "env"}:
            raise ValueError("category must be 'terraform' or 'env'")
        return v


class TFCPushVariablesRequest(BaseModel):
    """Push a batch of variables to a specific workspace."""

    workspace_id: str  # TFC workspace ID (ws-xxxx)
    variables: list[TFCVariableRequest]

    @field_validator("workspace_id")
    @classmethod
    def ws_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("workspace_id is required")
        return v


class TFCRunRequest(BaseModel):
    """Trigger a new run for a TFC workspace."""

    workspace_id: str  # TFC workspace ID
    message: str = ""
    auto_apply: bool = False

    @field_validator("workspace_id")
    @classmethod
    def ws_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("workspace_id is required")
        return v


class TFCRunActionRequest(BaseModel):
    """Apply or discard confirmation with optional comment."""

    comment: str = ""


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TFCWorkspaceResponse(BaseModel):
    """Serialised TFC workspace for API consumers."""

    id: str
    name: str
    org_name: str = ""
    execution_mode: str
    auto_apply: bool
    locked: bool
    terraform_version: str = ""
    working_directory: str = ""
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TFCVariableResponse(BaseModel):
    """Serialised TFC variable — value omitted when sensitive."""

    id: str
    key: str
    value: str = ""       # empty string when sensitive=True
    category: str
    sensitive: bool
    description: str = ""
    hcl: bool = False

    model_config = {"from_attributes": True}


class TFCRunResponse(BaseModel):
    """Serialised TFC run."""

    id: str
    status: str
    message: str = ""
    auto_apply: bool
    is_destroy: bool
    workspace_id: str = ""
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TFCSyncResponse(BaseModel):
    """Result of a project → TFC sync operation."""

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    total_modules: int = 0


class TFCSetupResponse(BaseModel):
    """Confirmation that TFC credentials were stored."""

    project_id: str
    org_name: str
    connected: bool = True
    message: str = "TFC credentials stored successfully"


class TFCPushVariablesResponse(BaseModel):
    """Result of a push-variables operation."""

    workspace_id: str
    created: list[str] = []
    updated: list[str] = []
