"""Simple cost estimation from terraform plan JSON output.

Uses a static lookup table for MVP. Full Infracost integration is deferred
to Phase 7. All costs are approximate monthly USD figures.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.core.models import CostEstimate, ResourceCost

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static monthly cost lookup table (USD, approximate us-east-1 on-demand)
# ---------------------------------------------------------------------------
# Format: resource_type -> monthly_usd
# Where the cost is for the most common / smallest SKU.
# Multi-instance costs are multiplied at estimation time.

_COST_TABLE: dict[str, float] = {
    # EC2 instances (t3.micro baseline)
    "aws_instance": 8.47,
    "aws_launch_template": 0.0,  # template itself has no cost
    "aws_autoscaling_group": 0.0,  # cost comes from instances it launches

    # Load balancers
    "aws_lb": 16.20,          # ALB: ~$16/mo base + LCU charges
    "aws_lb_listener": 0.0,
    "aws_lb_target_group": 0.0,

    # NAT Gateway (~$32/mo base + data transfer)
    "aws_nat_gateway": 32.40,
    "aws_eip": 3.60,          # idle EIP cost

    # Storage
    "aws_s3_bucket": 0.0,     # pay-per-use, no fixed monthly
    "aws_ebs_volume": 8.00,   # 100 GB gp3 @ $0.08/GB
    "aws_efs_file_system": 3.00,  # 10 GB @ $0.30/GB

    # RDS (db.t3.micro)
    "aws_db_instance": 15.33,
    "aws_rds_cluster": 73.00,  # Aurora serverless minimum

    # ElastiCache (cache.t3.micro)
    "aws_elasticache_cluster": 12.24,

    # DynamoDB (pay-per-use, estimate for 1M reads/writes)
    "aws_dynamodb_table": 1.25,

    # Lambda (first 1M requests free, estimate for moderate use)
    "aws_lambda_function": 0.20,

    # Networking (no fixed monthly for most)
    "aws_vpc": 0.0,
    "aws_subnet": 0.0,
    "aws_internet_gateway": 0.0,
    "aws_security_group": 0.0,
    "aws_security_group_rule": 0.0,
    "aws_route_table": 0.0,
    "aws_route_table_association": 0.0,

    # IAM (no cost)
    "aws_iam_role": 0.0,
    "aws_iam_policy": 0.0,
    "aws_iam_role_policy_attachment": 0.0,
    "aws_iam_instance_profile": 0.0,

    # Misc AWS
    "aws_cloudwatch_log_group": 0.50,  # estimate for 1 GB/mo ingestion
    "aws_sns_topic": 0.50,
    "aws_sqs_queue": 0.40,
    "aws_ssm_parameter": 0.05,
    "aws_secretsmanager_secret": 0.40,

    # EKS
    "aws_eks_cluster": 72.00,   # $0.10/hr control plane
    "aws_eks_node_group": 8.47,  # per node (t3.micro baseline)

    # Proxmox (self-hosted, estimate electricity/licensing cost)
    "proxmox_vm_qemu": 5.00,
    "proxmox_lxc": 2.00,

    # Meta-resources (no cost)
    "null_resource": 0.0,
    "random_id": 0.0,
    "random_string": 0.0,
    "random_password": 0.0,
    "time_sleep": 0.0,
    "local_file": 0.0,
}

_DISCLAIMER = (
    "Cost estimates are approximate, based on us-east-1 on-demand pricing "
    "for smallest common SKUs. Actual costs depend on usage, region, and "
    "reserved/spot pricing. Use AWS Cost Calculator for accurate quotes."
)


def _extract_planned_resources(plan_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract resource_changes that result in a create or replace action."""
    planned: list[dict[str, Any]] = []
    for rc in plan_json.get("resource_changes", []):
        actions = rc.get("change", {}).get("actions", [])
        if any(a in ("create", "replace") for a in actions):
            planned.append(rc)
    return planned


def estimate_from_plan(plan_json: dict[str, Any]) -> CostEstimate:
    """Build a cost estimate from terraform plan JSON output.

    Iterates resource_changes looking for create/replace actions and sums
    their monthly costs using the static lookup table.

    Args:
        plan_json: Parsed dict from `terraform plan -json` output.

    Returns:
        CostEstimate with total and per-resource breakdown.
    """
    planned = _extract_planned_resources(plan_json)
    breakdown: list[ResourceCost] = []
    total = 0.0

    for rc in planned:
        rtype = rc.get("type", "")
        address = rc.get("address", rtype)
        monthly = _COST_TABLE.get(rtype, 0.0)

        if monthly > 0 or rtype in _COST_TABLE:
            breakdown.append(
                ResourceCost(
                    resource_type=rtype,
                    resource_address=address,
                    monthly_usd=monthly,
                    notes="Static estimate" if monthly > 0 else "No fixed monthly cost",
                )
            )
            total += monthly
        else:
            logger.debug("No cost data for resource type '%s', defaulting to $0", rtype)
            breakdown.append(
                ResourceCost(
                    resource_type=rtype,
                    resource_address=address,
                    monthly_usd=0.0,
                    notes="Unknown resource type — cost not estimated",
                )
            )

    logger.info(
        "Cost estimate: $%.2f/mo for %d resources", total, len(planned)
    )

    return CostEstimate(
        total_monthly_usd=round(total, 2),
        breakdown=breakdown,
        currency="USD",
        disclaimer=_DISCLAIMER,
    )


def check_threshold(estimate: CostEstimate, max_monthly: float) -> bool:
    """Check whether estimated cost is within the allowed monthly budget.

    Args:
        estimate: CostEstimate from estimate_from_plan().
        max_monthly: Maximum allowed monthly spend in USD.

    Returns:
        True if within budget, False if estimate exceeds max_monthly.
    """
    within = estimate.total_monthly_usd <= max_monthly
    if not within:
        logger.warning(
            "Cost estimate $%.2f exceeds threshold $%.2f",
            estimate.total_monthly_usd,
            max_monthly,
        )
    return within
