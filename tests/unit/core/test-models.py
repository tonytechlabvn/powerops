"""Unit tests for backend.core.models — Pydantic schema validation."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.core.models import (
    ApplyResult,
    ChangeAction,
    CostEstimate,
    Job,
    JobStatus,
    JobType,
    PlanResult,
    Resource,
    ResourceChange,
    Template,
    TemplateMetadata,
    TemplateVariable,
    ValidationResult,
    Violation,
)


# ---------------------------------------------------------------------------
# JobStatus enum
# ---------------------------------------------------------------------------


def test_job_status_values() -> None:
    assert JobStatus.pending == "pending"
    assert JobStatus.running == "running"
    assert JobStatus.completed == "completed"
    assert JobStatus.failed == "failed"
    assert JobStatus.cancelled == "cancelled"


def test_job_status_from_string() -> None:
    assert JobStatus("pending") is JobStatus.pending
    assert JobStatus("failed") is JobStatus.failed


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------


def test_job_defaults() -> None:
    job = Job(id="abc123", type=JobType.plan)
    assert job.status == JobStatus.pending
    assert job.output == ""
    assert job.error == ""
    assert job.is_hidden is False
    assert isinstance(job.created_at, datetime)
    assert job.completed_at is None


def test_job_serialisation_round_trip() -> None:
    job = Job(id="xyz", type=JobType.apply, status=JobStatus.running)
    data = job.model_dump()
    restored = Job(**data)
    assert restored.id == job.id
    assert restored.status == job.status


def test_job_invalid_status_raises() -> None:
    with pytest.raises(ValidationError):
        Job(id="x", type=JobType.plan, status="not_a_status")


# ---------------------------------------------------------------------------
# PlanResult model
# ---------------------------------------------------------------------------


def test_plan_result_defaults() -> None:
    result = PlanResult(success=True)
    assert result.resource_changes == []
    assert result.raw_output == ""
    assert result.stderr == ""


def test_plan_result_with_changes() -> None:
    change = ResourceChange(
        address="aws_instance.web",
        type="aws_instance",
        name="web",
        action=ChangeAction.create,
    )
    result = PlanResult(success=True, resource_changes=[change])
    assert len(result.resource_changes) == 1
    assert result.resource_changes[0].action == ChangeAction.create


# ---------------------------------------------------------------------------
# ValidationResult model
# ---------------------------------------------------------------------------


def test_validation_result_valid() -> None:
    vr = ValidationResult(valid=True)
    assert vr.violations == []
    assert vr.errors == []
    assert vr.resources == []


def test_validation_result_with_violation() -> None:
    v = Violation(
        resource_type="aws_bad",
        resource_name="x",
        reason="Not allowed",
    )
    vr = ValidationResult(valid=False, violations=[v])
    assert not vr.valid
    assert vr.violations[0].resource_type == "aws_bad"


# ---------------------------------------------------------------------------
# Resource model
# ---------------------------------------------------------------------------


def test_resource_address_default_empty() -> None:
    r = Resource(type="aws_instance", name="web")
    assert r.address == ""
    assert r.attributes == {}


def test_resource_with_address() -> None:
    r = Resource(type="aws_instance", name="web", address="aws_instance.web")
    assert r.address == "aws_instance.web"


# ---------------------------------------------------------------------------
# TemplateVariable model
# ---------------------------------------------------------------------------


def test_template_variable_required_defaults_true() -> None:
    v = TemplateVariable(name="key_name")
    assert v.required is True
    assert v.type == "string"


def test_template_variable_with_default_sets_required_false() -> None:
    v = TemplateVariable(name="region", default="us-east-1", required=False)
    assert v.required is False
    assert v.default == "us-east-1"


# ---------------------------------------------------------------------------
# CostEstimate model
# ---------------------------------------------------------------------------


def test_cost_estimate_defaults() -> None:
    ce = CostEstimate(total_monthly_usd=0.0)
    assert ce.currency == "USD"
    assert ce.breakdown == []
    assert len(ce.disclaimer) > 0


def test_cost_estimate_serialisation() -> None:
    ce = CostEstimate(total_monthly_usd=42.5)
    data = ce.model_dump()
    assert data["total_monthly_usd"] == 42.5
    assert data["currency"] == "USD"
