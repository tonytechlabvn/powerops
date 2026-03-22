"""Pydantic schemas for Project CRUD endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    config_yaml: str = ""

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name is required")
        if len(v) > 128:
            raise ValueError("Project name must be 128 characters or fewer")
        return v


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config_yaml: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"draft", "active", "archived"}:
            raise ValueError("status must be draft, active, or archived")
        return v


class AddMemberRequest(BaseModel):
    user_id: str
    role_name: str = "user"
    assigned_modules: list[str] = []


class AddCredentialRequest(BaseModel):
    provider: str
    credential_json: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ProjectModuleResponse(BaseModel):
    id: str
    name: str
    path: str
    provider: str
    depends_on: list[str] = []
    status: str
    last_run_id: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectMemberResponse(BaseModel):
    user_id: str
    user_email: str = ""
    user_name: str = ""
    role_name: str
    assigned_modules: list[str] = []
    joined_at: datetime

    model_config = {"from_attributes": True}


class ProjectRunResponse(BaseModel):
    id: str
    module_id: str
    module_name: str = ""
    user_id: str
    run_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    module_count: int = 0
    member_count: int = 0

    model_config = {"from_attributes": True}


class ProjectDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    config_yaml: str
    status: str
    org_id: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    modules: list[ProjectModuleResponse] = []
    members: list[ProjectMemberResponse] = []
    runs: list[ProjectRunResponse] = []

    model_config = {"from_attributes": True}


class ProjectCredentialResponse(BaseModel):
    """Never exposes raw credential data — write-only."""
    id: str
    provider: str
    is_sensitive: bool
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
