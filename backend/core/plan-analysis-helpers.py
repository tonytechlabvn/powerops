"""Deterministic plan analysis helpers for Phase 9 AI Plan Explainer.

Extracts structured summaries, risk assessments, and cost signals from
terraform plan JSON without calling the AI — used to pre-process data
before sending to Claude and to hydrate structured response schemas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Resource types that warrant elevated risk flags
_DATA_LOSS_TYPES = frozenset({
    "aws_db_instance", "aws_rds_cluster", "aws_dynamodb_table",
    "aws_s3_bucket", "aws_efs_file_system", "aws_ebs_volume",
})
_SECURITY_TYPES = frozenset({
    "aws_security_group", "aws_security_group_rule",
    "aws_iam_role", "aws_iam_policy", "aws_iam_role_policy_attachment",
    "aws_iam_instance_profile",
})
_DOWNTIME_TYPES = frozenset({
    "aws_lb", "aws_lb_listener", "aws_lb_target_group",
    "aws_instance", "aws_autoscaling_group", "aws_eks_cluster",
})
# Rough monthly cost signals by resource type (USD)
_COST_SIGNALS: dict[str, float] = {
    "aws_instance": 30.0,
    "aws_eks_cluster": 70.0,
    "aws_rds_cluster": 100.0,
    "aws_db_instance": 50.0,
    "aws_nat_gateway": 35.0,
    "aws_lb": 20.0,
    "aws_elasticache_cluster": 40.0,
    "aws_lambda_function": 2.0,
}


@dataclass
class RiskFlag:
    type: str        # "data_loss" | "downtime" | "security"
    resource: str
    reason: str


@dataclass
class RiskAssessment:
    level: str       # "low" | "medium" | "high" | "critical"
    flags: list[RiskFlag] = field(default_factory=list)


@dataclass
class CostImpact:
    direction: str   # "increase" | "decrease" | "neutral"
    estimate: str    # e.g. "$50-100/month increase"


@dataclass
class PlanSummary:
    total_changes: int
    creates: int
    updates: int
    destroys: int
    replacements: int
    resource_types: list[str]
    affected_modules: list[str]


def extract_plan_summary(plan_json: dict) -> PlanSummary:
    """Extract structured change counts and resource types from terraform plan JSON."""
    changes = plan_json.get("resource_changes", [])
    creates = updates = destroys = replacements = 0
    resource_types: set[str] = set()
    modules: set[str] = set()

    for ch in changes:
        actions = ch.get("change", {}).get("actions", [])
        rtype = ch.get("type", "")
        address = ch.get("address", "")
        if rtype:
            resource_types.add(rtype)
        # Extract module prefix if present (e.g. "module.vpc.aws_vpc.main" -> "module.vpc")
        if address.startswith("module."):
            parts = address.split(".")
            if len(parts) >= 2:
                modules.add(f"{parts[0]}.{parts[1]}")

        if actions == ["no-op"] or actions == ["read"]:
            continue
        if "create" in actions and "delete" in actions:
            replacements += 1
        elif "create" in actions:
            creates += 1
        elif "update" in actions:
            updates += 1
        elif "delete" in actions:
            destroys += 1

    return PlanSummary(
        total_changes=creates + updates + destroys + replacements,
        creates=creates,
        updates=updates,
        destroys=destroys,
        replacements=replacements,
        resource_types=sorted(resource_types),
        affected_modules=sorted(modules),
    )


def assess_risk(plan_json: dict) -> RiskAssessment:
    """Assess risk level of plan changes using deterministic rules.

    Returns RiskAssessment with level (low/medium/high/critical) and flags.
    """
    changes = plan_json.get("resource_changes", [])
    flags: list[RiskFlag] = []

    for ch in changes:
        actions = ch.get("change", {}).get("actions", [])
        rtype = ch.get("type", "")
        address = ch.get("address", address := ch.get("address", "unknown"))

        is_destroy = "delete" in actions
        is_replace = "create" in actions and "delete" in actions

        if (is_destroy or is_replace) and rtype in _DATA_LOSS_TYPES:
            flags.append(RiskFlag(
                type="data_loss",
                resource=address,
                reason=f"Destroying {rtype} may cause irreversible data loss.",
            ))
        if ("create" in actions or "update" in actions) and rtype in _SECURITY_TYPES:
            flags.append(RiskFlag(
                type="security",
                resource=address,
                reason=f"Modifying {rtype} changes access controls.",
            ))
        if (is_destroy or is_replace) and rtype in _DOWNTIME_TYPES:
            flags.append(RiskFlag(
                type="downtime",
                resource=address,
                reason=f"Replacing {rtype} may cause service interruption.",
            ))

    # Determine overall level
    types_seen = {f.type for f in flags}
    data_loss = "data_loss" in types_seen
    security = "security" in types_seen
    downtime = "downtime" in types_seen

    if data_loss and (security or downtime):
        level = "critical"
    elif data_loss:
        level = "high"
    elif security or downtime:
        level = "medium"
    elif flags:
        level = "medium"
    else:
        level = "low"

    return RiskAssessment(level=level, flags=flags)


def estimate_cost_impact(plan_json: dict) -> CostImpact:
    """Produce a rough cost impact estimate based on resource types being created/deleted."""
    changes = plan_json.get("resource_changes", [])
    delta = 0.0

    for ch in changes:
        actions = ch.get("change", {}).get("actions", [])
        rtype = ch.get("type", "")
        cost = _COST_SIGNALS.get(rtype, 0.0)
        if cost == 0.0:
            continue
        if "create" in actions and "delete" not in actions:
            delta += cost
        elif "delete" in actions and "create" not in actions:
            delta -= cost

    if delta > 5:
        bucket = "$<10/month" if delta < 10 else f"${int(delta)}-{int(delta * 1.3)}/month"
        return CostImpact(direction="increase", estimate=f"~{bucket} increase")
    elif delta < -5:
        return CostImpact(direction="decrease", estimate=f"~${int(abs(delta))}/month savings")
    return CostImpact(direction="neutral", estimate="Minimal cost change expected")


def strip_sensitive_values(plan_json: dict) -> dict:
    """Remove sensitive attribute values before sending plan JSON to AI.

    Replaces any string value matching secret patterns with '[REDACTED]'.
    """
    import json
    import re

    _SECRET_RE = re.compile(
        r"(password|secret|key|token|credential|private)", re.IGNORECASE
    )

    def _scrub(obj):
        if isinstance(obj, dict):
            return {
                k: "[REDACTED]" if isinstance(v, str) and _SECRET_RE.search(k) else _scrub(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_scrub(i) for i in obj]
        return obj

    # Work on a deep copy via JSON round-trip to avoid mutating caller's dict
    return json.loads(json.dumps(_scrub(plan_json)))
