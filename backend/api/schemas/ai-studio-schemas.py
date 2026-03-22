"""Pydantic schemas for AI Studio endpoints.

Used by ai-studio-routes.py for request validation and response serialization.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class GenerateTemplateRequest(BaseModel):
    description: str = Field(..., min_length=10, description="Natural language template requirements")
    providers: list[str] = Field(default=["aws"], description="Target providers: aws, proxmox, azurerm, google")
    complexity: str = Field("standard", description="Template complexity: simple | standard | complex")
    additional_context: str | None = Field(None, description="Extra context (e.g. graph JSON from canvas)")


class ExtractTemplateRequest(BaseModel):
    hcl_code: str = Field(..., min_length=10, description="Raw HCL code to convert into a template")
    template_name: str | None = Field(None, description="Optional template name — AI infers if not provided")


class RefineTemplateRequest(BaseModel):
    template_files: dict[str, str] = Field(..., description="Current template files keyed by filename")
    refinement: str = Field(..., min_length=3, description="What to change about the template")
    template_name: str = Field("", description="Template name for continuity")
    providers: list[str] = Field(default=["aws"])
    description: str = Field("", description="Template description for continuity")
    conversation_history: list[dict] | None = Field(None, description="Prior chat messages [{role, content}]")


class ValidateTemplateRequest(BaseModel):
    template_files: dict[str, str] = Field(..., description="Template files to validate")


class SaveTemplateRequest(BaseModel):
    template_name: str = Field(..., min_length=3, description="Template path e.g. 'hybrid/my-vpn'")
    files: dict[str, str] = Field(..., description="All template files keyed by filename")
    providers: list[str] = Field(default=["aws"])
    description: str = Field("")
    display_name: str = Field("")
    tags: list[str] = Field(default_factory=list)
    overwrite: bool = Field(False, description="Overwrite existing template if it exists")


class WizardStepsRequest(BaseModel):
    description: str = Field(..., min_length=10, description="NL description for wizard step analysis")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TemplateValidationResponse(BaseModel):
    valid: bool
    jinja2_errors: list[str] = Field(default_factory=list)
    hcl_errors: dict[str, list[str]] = Field(default_factory=dict)
    structure_warnings: list[str] = Field(default_factory=list)


class TemplateFileResponse(BaseModel):
    name: str
    providers: list[str]
    description: str
    display_name: str
    files: dict[str, str]
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    validation: TemplateValidationResponse | None = None


class SaveTemplateResponse(BaseModel):
    saved_path: str
    message: str


class WizardStepsResponse(BaseModel):
    steps: list[str] = Field(default_factory=list)
    defaults: dict[str, dict] = Field(default_factory=dict)
    reasoning: str = ""
