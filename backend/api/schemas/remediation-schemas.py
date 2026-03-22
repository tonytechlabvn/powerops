"""Pydantic schemas for AI remediation endpoints (Phase 10).

Used by remediation-routes.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RemediationRequest(BaseModel):
    error_output: str = Field(..., min_length=1, description="Full terraform error output")
    workspace_id: str = Field(..., description="Workspace ID to read HCL files from")
    failed_operation: str = Field("plan", description="Operation that failed: plan | apply | init")
    plan_json: dict | None = Field(None, description="Plan JSON if available for extra context")


class ApplyFixRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace ID to write fixed files to")
    fixes: list[FileFix] = Field(..., min_length=1)


class FileFix(BaseModel):
    file_path: str
    fixed_content: str
    description: str


class ErrorCategoryResponse(BaseModel):
    type: str
    is_code_fixable: bool
    severity: str


class FileFixResponse(BaseModel):
    file_path: str
    original_content: str
    fixed_content: str
    diff_lines: list[str]
    description: str


class RemediationResponse(BaseModel):
    error_category: ErrorCategoryResponse
    root_cause: str
    is_fixable: bool
    fixes: list[FileFixResponse] = Field(default_factory=list)
    explanation: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ApplyFixResponse(BaseModel):
    applied: list[str]
    failed: list[str]
    validation_errors: list[str] = Field(default_factory=list)
