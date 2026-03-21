package terrabot.policy.encryption_required

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_ebs_volume"
    resource.change.actions[_] != "delete"
    not resource.change.after.encrypted
    msg := {
        "resource": resource.address,
        "message": "EBS volume must have encryption enabled (set encrypted = true)",
        "severity": "high",
    }
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_db_instance"
    resource.change.actions[_] != "delete"
    not resource.change.after.storage_encrypted
    msg := {
        "resource": resource.address,
        "message": "RDS instance must have storage encryption enabled (set storage_encrypted = true)",
        "severity": "high",
    }
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_rds_cluster"
    resource.change.actions[_] != "delete"
    not resource.change.after.storage_encrypted
    msg := {
        "resource": resource.address,
        "message": "RDS cluster must have storage encryption enabled (set storage_encrypted = true)",
        "severity": "high",
    }
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] != "delete"
    not resource.change.after.server_side_encryption_configuration
    not resource.change.after.kms_key_id
    msg := {
        "resource": resource.address,
        "message": "S3 bucket must have server-side encryption configured (kms_key_id or server_side_encryption_configuration)",
        "severity": "medium",
    }
}
