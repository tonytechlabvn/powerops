package terrabot.policy.instance_size_limits

# Blocked instance type suffixes and exact types
_blocked_suffixes := {".metal", ".12xlarge", ".16xlarge", ".24xlarge", ".48xlarge"}

_is_blocked(instance_type) {
    suffix := _blocked_suffixes[_]
    endswith(instance_type, suffix)
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_instance"
    instance_type := resource.change.after.instance_type
    _is_blocked(instance_type)
    msg := {
        "resource": resource.address,
        "message": sprintf("Instance type '%v' is not permitted (metal and 12xlarge+ are blocked)", [instance_type]),
        "severity": "high",
    }
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_launch_template"
    instance_type := resource.change.after.instance_type
    _is_blocked(instance_type)
    msg := {
        "resource": resource.address,
        "message": sprintf("Launch template instance type '%v' is not permitted (metal and 12xlarge+ are blocked)", [instance_type]),
        "severity": "high",
    }
}
