"""Pydantic request/response schemas for the HCL file management API.

Used by hcl-file-routes.py. Kept separate from core models to allow
independent evolution of API contract vs. internal dataclasses.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FileInfoResponse(BaseModel):
    """Metadata for a single file or directory in the workspace."""
    path: str
    name: str
    size: int
    modified_at: str
    is_directory: bool
    checksum: str


class FileContentResponse(BaseModel):
    """Full content of a readable workspace file."""
    path: str
    content: str
    checksum: str
    size: int
    language: str   # Monaco language identifier: "hcl" | "json" | "yaml" | "text"


class WriteFileRequest(BaseModel):
    """Body for create (POST) and update (PUT) file endpoints."""
    content: str
    # Provide the checksum of the version you read to detect concurrent edits.
    # If omitted, last-write-wins.
    expected_checksum: str | None = None


class WriteFileResponse(BaseModel):
    """Confirmation of a successful write with optional HCL validation."""
    path: str
    checksum: str
    validation: ValidationResponse | None = None


class RenameFileRequest(BaseModel):
    """Body for the rename/move endpoint."""
    new_path: str


class CreateDirectoryRequest(BaseModel):
    """Body for the create-directory endpoint."""
    path: str


class SearchRequest(BaseModel):
    """Body for the workspace-wide file search endpoint."""
    query: str
    pattern: str = "**/*.tf"


class SearchResultResponse(BaseModel):
    """Single line match from a content search."""
    path: str
    line: int
    content: str
    context_before: str = ""
    context_after: str = ""


class ValidationResponse(BaseModel):
    """HCL syntax validation outcome."""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FileTreeResponse(BaseModel):
    """Response for the list-files (tree) endpoint."""
    workspace_id: str
    files: list[FileInfoResponse] = Field(default_factory=list)
