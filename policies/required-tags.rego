package terrabot.policy.required_tags

# Resource types that must carry standard tags
_taggable_types := {
    "aws_instance",
    "aws_s3_bucket",
    "aws_db_instance",
    "aws_rds_cluster",
    "aws_elasticache_cluster",
    "aws_lambda_function",
    "aws_eks_cluster",
    "aws_ecs_service",
    "aws_lb",
    "aws_alb",
}

_required_tags := {"environment", "owner", "cost-center"}

_missing_tags(tags) := missing {
    missing := {t | t := _required_tags[_]; not tags[t]}
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    _taggable_types[resource.type]
    # Only check resources being created or updated
    resource.change.actions[_] != "delete"
    tags := object.get(resource.change.after, "tags", {})
    missing := _missing_tags(tags)
    count(missing) > 0
    msg := {
        "resource": resource.address,
        "message": sprintf("Missing required tags: %v", [missing]),
        "severity": "medium",
    }
}
