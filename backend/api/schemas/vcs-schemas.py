"""Pydantic schemas for VCS integration endpoints (Phase 3).

Models:
  VCSConnectRequest     — body for POST /api/workspaces/{id}/vcs
  VCSConnectionResponse — response for VCS connection info
  VCSUpdateRequest      — body for PATCH /api/workspaces/{id}/vcs
  GitHubSetupResponse   — response for GET /api/vcs/github/setup
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VCSConnectRequest(BaseModel):
    """Request body to connect a workspace to a GitHub repository."""
    installation_id: int = Field(..., description="GitHub App installation ID")
    repo_full_name: str = Field(..., description="Full repo name e.g. org/repo")
    branch: str = Field("main", description="Target branch to track")
    working_directory: str = Field(".", description="Terraform working dir within repo")
    auto_apply: bool = Field(False, description="Auto-apply after successful plan")


class VCSConnectionResponse(BaseModel):
    """Response body for VCS connection queries."""
    id: str
    workspace_id: str
    installation_id: int
    repo_full_name: str
    branch: str
    working_directory: str
    auto_apply: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class VCSUpdateRequest(BaseModel):
    """Partial update for an existing VCS connection."""
    branch: str | None = Field(None, description="New branch to track")
    working_directory: str | None = Field(None, description="New terraform working dir")
    auto_apply: bool | None = Field(None, description="Toggle auto-apply")


class GitHubSetupResponse(BaseModel):
    """GitHub App manifest / installation setup URL."""
    manifest_url: str
