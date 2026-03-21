package terrabot.policy.no_public_s3

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.after.acl == "public-read"
    msg := {
        "resource": resource.address,
        "message": "S3 bucket must not be public-read",
        "severity": "high",
    }
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.after.acl == "public-read-write"
    msg := {
        "resource": resource.address,
        "message": "S3 bucket must not be public-read-write",
        "severity": "critical",
    }
}
