"""Pydantic schemas for Private Module Registry endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PublishModuleRequest(BaseModel):
    namespace: str
    name: str
    provider: str
    description: str = ""
    tags: list[str] = []

    @field_validator("namespace", "name", "provider")
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Field is required")
        if len(v) > 64:
            raise ValueError("Field must be 64 characters or fewer")
        return v


class PublishVersionRequest(BaseModel):
    version: str
    # archive_bytes provided via multipart upload; this covers JSON metadata fields

    @field_validator("version")
    @classmethod
    def valid_semver(cls, v: str) -> str:
        import re
        if not re.match(r"^\d+\.\d+\.\d+$", v.strip()):
            raise ValueError("Version must follow semver format: MAJOR.MINOR.PATCH")
        return v.strip()


class UpdateModuleRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class VariableDocResponse(BaseModel):
    name: str
    type: str
    description: str
    default: Optional[str] = None
    required: bool
    validation: Optional[str] = None


class OutputDocResponse(BaseModel):
    name: str
    description: str
    value: str


class ResourceDocResponse(BaseModel):
    type: str
    name: str
    provider: str


class ModuleVersionResponse(BaseModel):
    id: str
    module_id: str
    version: str
    archive_checksum: str
    readme_content: str
    variables: list[VariableDocResponse] = []
    outputs: list[OutputDocResponse] = []
    resources: list[ResourceDocResponse] = []
    is_deprecated: bool
    published_by: str
    published_at: datetime

    model_config = {"from_attributes": True}


class ModuleResponse(BaseModel):
    id: str
    namespace: str
    name: str
    provider: str
    description: str
    org_id: str
    tags: list[str]
    is_deprecated: bool
    published_by: str
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    latest_version: Optional[str] = None

    model_config = {"from_attributes": True}


class ModuleDetailResponse(ModuleResponse):
    versions: list[ModuleVersionResponse] = []


# ---------------------------------------------------------------------------
# Terraform Registry Protocol v1 shapes
# ---------------------------------------------------------------------------

class TerraformVersionItem(BaseModel):
    version: str
    protocols: list[str] = ["4.0", "5.1"]
    platforms: list[dict] = []


class TerraformVersionsResponse(BaseModel):
    modules: list[dict]
