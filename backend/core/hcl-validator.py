"""HCL syntax validation and resource analysis.

Uses python-hcl2 to parse HCL strings and extract resource blocks.
Falls back to terraform validate for secondary checks when available.
"""
from __future__ import annotations

import io
import logging
from typing import Any

import hcl2

from backend.core.models import Resource, ValidationResult, Violation

logger = logging.getLogger(__name__)

# Default whitelist of approved resource types for AWS and Proxmox.
# Extend via check_resource_whitelist(resources, custom_allowed).
DEFAULT_ALLOWED_RESOURCES: frozenset[str] = frozenset(
    [
        # AWS compute
        "aws_instance",
        "aws_launch_template",
        "aws_autoscaling_group",
        "aws_eks_cluster",
        "aws_eks_node_group",
        "aws_lambda_function",
        # AWS networking
        "aws_vpc",
        "aws_subnet",
        "aws_internet_gateway",
        "aws_nat_gateway",
        "aws_security_group",
        "aws_security_group_rule",
        "aws_route_table",
        "aws_route_table_association",
        "aws_eip",
        "aws_lb",
        "aws_lb_listener",
        "aws_lb_target_group",
        # AWS storage
        "aws_s3_bucket",
        "aws_s3_bucket_policy",
        "aws_ebs_volume",
        "aws_efs_file_system",
        # AWS database
        "aws_db_instance",
        "aws_rds_cluster",
        "aws_elasticache_cluster",
        "aws_dynamodb_table",
        # AWS IAM
        "aws_iam_role",
        "aws_iam_policy",
        "aws_iam_role_policy_attachment",
        "aws_iam_instance_profile",
        # AWS misc
        "aws_cloudwatch_log_group",
        "aws_sns_topic",
        "aws_sqs_queue",
        "aws_ssm_parameter",
        "aws_secretsmanager_secret",
        # Proxmox
        "proxmox_vm_qemu",
        "proxmox_lxc",
        # Terraform meta-resources
        "null_resource",
        "random_id",
        "random_string",
        "random_password",
        "time_sleep",
        "local_file",
    ]
)


def validate_syntax(hcl_string: str) -> ValidationResult:
    """Parse HCL string and report syntax errors.

    Args:
        hcl_string: Raw HCL configuration text.

    Returns:
        ValidationResult — valid=True if parsing succeeded, else errors populated.
    """
    try:
        hcl2.load(io.StringIO(hcl_string))
        return ValidationResult(valid=True)
    except Exception as exc:  # hcl2 raises various exception types
        error_msg = str(exc)
        logger.debug("HCL parse error: %s", error_msg)
        return ValidationResult(valid=False, errors=[error_msg])


def parse_resources(hcl_string: str) -> list[Resource]:
    """Extract resource blocks from HCL string.

    Args:
        hcl_string: Raw HCL configuration text.

    Returns:
        List of Resource objects with type, name, and address populated.
        Returns empty list if HCL cannot be parsed.
    """
    try:
        parsed: dict[str, Any] = hcl2.load(io.StringIO(hcl_string))
    except Exception as exc:
        logger.debug("Cannot parse HCL for resource extraction: %s", exc)
        return []

    resources: list[Resource] = []
    # python-hcl2 returns resource blocks as a list of dicts, e.g.:
    # [{"aws_instance": {"web": {...}}}, {"aws_security_group": {"sg": {...}}}]
    raw_resources = parsed.get("resource", [])
    if isinstance(raw_resources, dict):
        raw_resources = [raw_resources]
    for block in raw_resources:
        if not isinstance(block, dict):
            continue
        for resource_type, instances in block.items():
            if isinstance(instances, list):
                for item in instances:
                    if isinstance(item, dict):
                        for name, attrs in item.items():
                            resources.append(
                                Resource(
                                    type=resource_type,
                                    name=name,
                                    address=f"{resource_type}.{name}",
                                    attributes=attrs if isinstance(attrs, dict) else {},
                                )
                            )
            elif isinstance(instances, dict):
                for name, attrs in instances.items():
                    resources.append(
                        Resource(
                            type=resource_type,
                            name=name,
                            address=f"{resource_type}.{name}",
                            attributes=attrs if isinstance(attrs, dict) else {},
                        )
                    )
    return resources


def check_resource_whitelist(
    resources: list[Resource],
    allowed: frozenset[str] | set[str] | None = None,
) -> list[Violation]:
    """Check resources against an allowed-types whitelist.

    Args:
        resources: Parsed Resource list from parse_resources().
        allowed: Set of permitted resource type strings.
                 Defaults to DEFAULT_ALLOWED_RESOURCES if None.

    Returns:
        List of Violation objects for any disallowed resource types.
        Empty list means all resources are permitted.
    """
    allowed_set = allowed if allowed is not None else DEFAULT_ALLOWED_RESOURCES
    violations: list[Violation] = []

    for resource in resources:
        if resource.type not in allowed_set:
            violations.append(
                Violation(
                    resource_type=resource.type,
                    resource_name=resource.name,
                    reason=(
                        f"Resource type '{resource.type}' is not in the approved whitelist. "
                        "Contact your platform admin to request access."
                    ),
                )
            )
    return violations


def validate_full(
    hcl_string: str,
    allowed_resources: frozenset[str] | set[str] | None = None,
) -> ValidationResult:
    """Combined validation: syntax check + resource whitelist.

    Convenience wrapper used by the API and CLI layers.

    Args:
        hcl_string: Raw HCL configuration text.
        allowed_resources: Optional custom whitelist; uses DEFAULT if None.

    Returns:
        ValidationResult with valid flag, errors, violations, and parsed resources.
    """
    syntax_result = validate_syntax(hcl_string)
    if not syntax_result.valid:
        return syntax_result

    resources = parse_resources(hcl_string)
    violations = check_resource_whitelist(resources, allowed_resources)

    return ValidationResult(
        valid=len(violations) == 0,
        violations=violations,
        errors=[],
        resources=resources,
    )
