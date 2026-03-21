"""Pydantic schemas for the Terraform HTTP state backend API (Phase 1).

LockInfoRequest/Response mirror the Terraform lock info payload exactly so
Terraform CLI interoperates without modification.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LockInfoRequest(BaseModel):
    """Terraform lock info payload sent on LOCK / UNLOCK requests."""

    ID: str = Field(default="", description="Unique lock identifier (UUID).")
    Operation: str = Field(default="", description="Terraform operation holding the lock.")
    Info: str = Field(default="", description="Human-readable lock context.")
    Who: str = Field(default="", description="User or process holding the lock.")
    Version: str = Field(default="", description="Terraform CLI version.")
    Created: str = Field(default="", description="ISO-8601 timestamp when lock was created.")
    Path: str = Field(default="", description="Remote state path.")


class LockInfoResponse(BaseModel):
    """Lock info returned to Terraform CLI."""

    ID: str = ""
    Operation: str = ""
    Info: str = ""
    Who: str = ""
    Version: str = ""
    Created: str = ""
    Path: str = ""


class StateVersionResponse(BaseModel):
    """Metadata for a single stored state version (no raw state data)."""

    id: str
    serial: int
    lineage: str
    checksum: str
    resource_count: int = 0
    created_at: str
    created_by: str


class StateOutputsResponse(BaseModel):
    """Non-sensitive workspace outputs extracted from the latest state."""

    outputs: dict[str, Any] = Field(default_factory=dict)
