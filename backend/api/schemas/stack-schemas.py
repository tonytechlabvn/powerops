"""Pydantic schemas for Stack Composition endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Stack definition sub-models
# ---------------------------------------------------------------------------

class StackModuleEntry(BaseModel):
    """One module entry in a stack definition."""
    name: str                          # local name within the stack (e.g. "networking")
    source: str                        # registry path: "namespace/name/provider"
    version: str                       # pinned semver
    variables: dict[str, str] = {}     # variable bindings (value or expression)
    depends_on: list[str] = []         # names of other modules this depends on


class StackVariableEntry(BaseModel):
    """Top-level variable exposed by the stack."""
    name: str
    type: str = "string"
    description: str = ""
    default: Optional[str] = None


class StackDefinition(BaseModel):
    modules: list[StackModuleEntry]
    variables: list[StackVariableEntry] = []


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateStackTemplateRequest(BaseModel):
    name: str
    description: str = ""
    definition: StackDefinition
    tags: list[str] = []

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Stack template name is required")
        if len(v) > 128:
            raise ValueError("Name must be 128 characters or fewer")
        return v


class UpdateStackTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[StackDefinition] = None
    tags: Optional[list[str]] = None


class ComposeProjectRequest(BaseModel):
    """Compose a project workspace from a stack definition."""
    project_id: str
    stack_definition: StackDefinition
    registry_url: str = "powerops.tonytechlab.com"


class CreateProjectFromTemplateRequest(BaseModel):
    """Instantiate a project from a saved stack template."""
    project_name: str
    variable_overrides: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class UpgradeInfoResponse(BaseModel):
    module_name: str
    current_version: str
    latest_version: str
    source: str


class ComposeResultResponse(BaseModel):
    project_id: str
    generated_files: dict[str, str]   # filename -> HCL content
    warnings: list[str] = []


class StackTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    org_id: str
    definition_json: str
    tags: list[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    module_count: int = 0

    model_config = {"from_attributes": True}


class MigrationResultResponse(BaseModel):
    template_name: str
    success: bool
    stack_template_id: Optional[str] = None
    modules_created: int = 0
    error: Optional[str] = None
