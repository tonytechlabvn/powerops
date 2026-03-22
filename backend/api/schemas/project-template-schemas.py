"""Pydantic schemas for project template and AI wizard endpoints."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Template response schemas
# ---------------------------------------------------------------------------

class TemplateResponse(BaseModel):
    """Summary metadata for a project template — used in list endpoint."""
    name: str
    display_name: str
    description: str
    category: str
    complexity: str
    providers: list[str]
    tags: list[str]
    module_count: int


class TemplateVariableSchema(BaseModel):
    """A single configurable variable within a template."""
    name: str
    type: str = "string"
    default: Optional[Any] = None
    description: str = ""


class TemplateModuleSchema(BaseModel):
    """A module entry within a template definition."""
    name: str
    provider: str
    depends_on: list[str] = []
    description: str = ""


class TemplateOutputSchema(BaseModel):
    """An output value declared by a template."""
    name: str
    module: str
    description: str = ""


class TemplateDetailResponse(BaseModel):
    """Full template detail including variables, modules, and outputs."""
    name: str
    display_name: str
    description: str
    category: str
    complexity: str
    providers: list[str]
    tags: list[str]
    variables: list[TemplateVariableSchema] = []
    modules: list[TemplateModuleSchema] = []
    roles: list[str] = []
    outputs: list[TemplateOutputSchema] = []


# ---------------------------------------------------------------------------
# Project creation from template
# ---------------------------------------------------------------------------

class CreateFromTemplateRequest(BaseModel):
    """Request body for POST /api/project-templates/{name}/create."""
    project_name: str = ""
    variables: dict[str, Any] = {}

    @field_validator("project_name")
    @classmethod
    def name_max_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 128:
            raise ValueError("project_name must be 128 characters or fewer")
        return v


class CreateFromTemplateResponse(BaseModel):
    """Response after creating a project from a template."""
    project_id: str
    project_name: str
    template_name: str


# ---------------------------------------------------------------------------
# Wizard schemas
# ---------------------------------------------------------------------------

class WizardMessage(BaseModel):
    """A single message in the wizard conversation history."""
    role: str  # "user" or "assistant"
    content: str


class WizardMessageRequest(BaseModel):
    """Request body for POST /api/project-wizard/message."""
    message: str
    history: list[WizardMessage] = []

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 4000:
            raise ValueError("message must be 4000 characters or fewer")
        return v


class WizardMessageResponse(BaseModel):
    """Response from the wizard chat endpoint."""
    response: str
    # Populated when the response contains a parseable ```yaml block
    project_yaml: Optional[str] = None


class WizardConfirmRequest(BaseModel):
    """Request body for POST /api/project-wizard/confirm."""
    project_yaml: str
    project_name: str = ""

    @field_validator("project_yaml")
    @classmethod
    def yaml_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("project_yaml must not be empty")
        return v

    @field_validator("project_name")
    @classmethod
    def name_max_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 128:
            raise ValueError("project_name must be 128 characters or fewer")
        return v
