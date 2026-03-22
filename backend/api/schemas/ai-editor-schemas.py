"""Pydantic request/response schemas for AI editor endpoints (Phase 8).

Used by ai-editor-routes.py. Kept in a separate schema file following
the project convention of one schema module per feature area.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, description="Natural language description of HCL to generate")
    current_file: str | None = Field(None, description="Name of the file currently open in editor")
    current_content: str | None = Field(None, description="Current content of the open file")
    provider: str = Field("aws", description="Target cloud provider: aws | proxmox | azurerm | google")


class ExplainRequest(BaseModel):
    code: str = Field(..., min_length=1, description="HCL block to explain")
    file_path: str | None = Field(None, description="Source file path for context")


class FixRequest(BaseModel):
    code: str = Field(..., min_length=1, description="HCL code that contains the error")
    error: str = Field(..., min_length=1, description="Terraform error message")
    file_path: str | None = Field(None, description="Source file path for context")


class CompleteRequest(BaseModel):
    code: str = Field(..., description="Full file content up to cursor")
    cursor_line: int = Field(..., ge=0, description="Zero-based line index of cursor")
    cursor_col: int = Field(..., ge=0, description="Zero-based column index of cursor")
    file_path: str | None = Field(None, description="Source file path for context")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    current_file: str | None = None
    current_content: str | None = None


class CompletionResponse(BaseModel):
    suggestion: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
