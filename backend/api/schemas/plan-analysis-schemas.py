"""Pydantic schemas for plan analysis and AI explanation endpoints (Phase 9).

Used by plan-analysis-routes.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanExplainRequest(BaseModel):
    plan_json: dict = Field(..., description="Terraform plan JSON from 'terraform show -json'")
    workspace_id: str | None = Field(None, description="Workspace ID for audit context")


class RiskFlagResponse(BaseModel):
    type: str       # "data_loss" | "downtime" | "security"
    resource: str
    reason: str


class RiskAssessmentResponse(BaseModel):
    level: str      # "low" | "medium" | "high" | "critical"
    flags: list[RiskFlagResponse] = Field(default_factory=list)


class CostImpactResponse(BaseModel):
    direction: str  # "increase" | "decrease" | "neutral"
    estimate: str


class PlanSummaryResponse(BaseModel):
    total_changes: int
    creates: int
    updates: int
    destroys: int
    replacements: int
    resource_types: list[str]
    affected_modules: list[str]


class PlanAnalysisResponse(BaseModel):
    """Deterministic plan analysis — no AI, instant response."""
    summary: PlanSummaryResponse
    risk: RiskAssessmentResponse
    cost: CostImpactResponse
