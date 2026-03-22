"""Pydantic schemas for AI module generator endpoints (Phase 11).

Used by module-generator-routes.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateModuleRequest(BaseModel):
    description: str = Field(..., min_length=10, description="Natural language module requirements")
    provider: str = Field("aws", description="Target provider: aws | azurerm | google | proxmox")
    complexity: str = Field("standard", description="Module complexity: simple | standard | complex")
    additional_context: str | None = Field(None, description="Extra context or constraints")


class RefineModuleRequest(BaseModel):
    module_files: dict[str, str] = Field(..., description="Current module files keyed by filename")
    refinement: str = Field(..., min_length=5, description="What to change about the module")
    provider: str = Field("aws")
    name: str = Field("", description="Original module name for continuity")
    description: str = Field("", description="Original module description for continuity")


class ValidateModuleRequest(BaseModel):
    module_files: dict[str, str] = Field(..., description="Module files keyed by filename")


class PublishModuleRequest(BaseModel):
    module_files: dict[str, str]
    namespace: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    provider: str = Field("aws")
    version: str = Field("1.0.0")
    description: str = Field("")
    tags: list[str] = Field(default_factory=list)


class ModuleValidationResponse(BaseModel):
    valid: bool
    file_errors: dict[str, list[str]] = Field(default_factory=dict)
    structure_warnings: list[str] = Field(default_factory=list)


class GeneratedModuleResponse(BaseModel):
    name: str
    provider: str
    description: str
    files: dict[str, str]
    resources: list[str] = Field(default_factory=list)
    validation: ModuleValidationResponse | None = None
