"""Unit tests for backend.core.cost-estimator."""
from __future__ import annotations

import pytest

from backend.core.cost_estimator import check_threshold, estimate_from_plan
from backend.core.models import CostEstimate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plan_with(*resource_types: str) -> dict:
    """Build a minimal plan JSON with given resource types all being created."""
    return {
        "resource_changes": [
            {
                "address": f"{rtype}.test",
                "type": rtype,
                "name": "test",
                "change": {"actions": ["create"]},
            }
            for rtype in resource_types
        ]
    }


# ---------------------------------------------------------------------------
# estimate_from_plan
# ---------------------------------------------------------------------------


def test_estimate_from_plan_known_resources(sample_plan_json: dict) -> None:
    """plan-create.json has aws_instance ($8.47) + aws_security_group ($0.00)."""
    estimate = estimate_from_plan(sample_plan_json)
    assert isinstance(estimate, CostEstimate)
    assert estimate.total_monthly_usd == pytest.approx(8.47)
    assert len(estimate.breakdown) == 2


def test_estimate_from_plan_unknown_resource_defaults_to_zero() -> None:
    plan = _plan_with("aws_completely_unknown_resource")
    estimate = estimate_from_plan(plan)
    assert estimate.total_monthly_usd == 0.0
    assert len(estimate.breakdown) == 1
    assert estimate.breakdown[0].monthly_usd == 0.0


def test_estimate_from_plan_empty_plan() -> None:
    estimate = estimate_from_plan({"resource_changes": []})
    assert estimate.total_monthly_usd == 0.0
    assert estimate.breakdown == []


def test_estimate_from_plan_skips_delete_actions() -> None:
    """Delete/update actions should not be costed."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_instance.web",
                "type": "aws_instance",
                "name": "web",
                "change": {"actions": ["delete"]},
            }
        ]
    }
    estimate = estimate_from_plan(plan)
    assert estimate.total_monthly_usd == 0.0
    assert estimate.breakdown == []


def test_estimate_from_plan_counts_replace_actions() -> None:
    """Replace = destroy + create; should be costed."""
    plan = {
        "resource_changes": [
            {
                "address": "aws_instance.web",
                "type": "aws_instance",
                "name": "web",
                "change": {"actions": ["replace"]},
            }
        ]
    }
    estimate = estimate_from_plan(plan)
    assert estimate.total_monthly_usd == pytest.approx(8.47)


def test_estimate_from_plan_sums_multiple_resources() -> None:
    plan = _plan_with("aws_instance", "aws_lb", "aws_nat_gateway")
    estimate = estimate_from_plan(plan)
    # 8.47 + 16.20 + 32.40
    assert estimate.total_monthly_usd == pytest.approx(57.07)


def test_estimate_from_plan_has_disclaimer() -> None:
    estimate = estimate_from_plan({"resource_changes": []})
    assert len(estimate.disclaimer) > 0


# ---------------------------------------------------------------------------
# check_threshold
# ---------------------------------------------------------------------------


def test_check_threshold_within_budget() -> None:
    estimate = CostEstimate(total_monthly_usd=50.0)
    assert check_threshold(estimate, max_monthly=100.0) is True


def test_check_threshold_at_exact_limit() -> None:
    estimate = CostEstimate(total_monthly_usd=100.0)
    assert check_threshold(estimate, max_monthly=100.0) is True


def test_check_threshold_over_budget() -> None:
    estimate = CostEstimate(total_monthly_usd=150.0)
    assert check_threshold(estimate, max_monthly=100.0) is False


def test_check_threshold_zero_budget() -> None:
    estimate = CostEstimate(total_monthly_usd=0.01)
    assert check_threshold(estimate, max_monthly=0.0) is False
