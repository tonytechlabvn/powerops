"""Pydantic schemas for VCS plan run endpoints (Phase 4).

Models:
  VCSPlanRunResponse         — response for a VCSPlanRun record
  TriggerPatternItem         — single branch->action mapping
  VCSWorkflowConfigRequest   — body for PATCH /api/workspaces/{id}/vcs-workflow
  VCSWorkflowConfigResponse  — current trigger pattern config
  ReplanRequest              — body for POST .../replan
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VCSPlanRunResponse(BaseModel):
    """Single VCS-triggered plan run record."""
    id: str
    vcs_connection_id: str
    workspace_id: str
    pr_number: int
    commit_sha: str
    branch: str
    status: str                  # pending | running | completed | failed | cancelled
    plan_output: str
    plan_summary_json: str       # JSON string: {adds, changes, destroys}
    policy_passed: bool | None
    comment_id: int | None
    job_id: str | None
    triggered_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class TriggerPatternItem(BaseModel):
    """Maps a branch glob pattern to a VCS action."""
    branch: str = Field(..., description="Branch name or glob (e.g. 'main', 'feature/*')")
    action: str = Field(..., description="'plan' or 'apply'")


class VCSWorkflowConfigRequest(BaseModel):
    """Request body to update VCS workflow trigger patterns."""
    trigger_patterns: list[TriggerPatternItem] = Field(
        default_factory=lambda: [
            TriggerPatternItem(branch="main", action="apply"),
            TriggerPatternItem(branch="*", action="plan"),
        ],
        description="Ordered list of branch->action mappings",
    )
    auto_apply: bool | None = Field(None, description="Override auto_apply on the VCSConnection")


class VCSWorkflowConfigResponse(BaseModel):
    """Current VCS workflow configuration for a workspace."""
    workspace_id: str
    repo_full_name: str
    branch: str
    auto_apply: bool
    trigger_patterns: list[TriggerPatternItem]


class ReplanRequest(BaseModel):
    """Optional body for manual replan trigger."""
    commit_sha: str | None = Field(None, description="SHA to plan; defaults to PR head SHA")
