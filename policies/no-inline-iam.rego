package terrabot.policy.no_inline_iam

# Inline IAM user policies expand blast radius and bypass central policy review.
# Use aws_iam_policy + aws_iam_user_policy_attachment instead.

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_iam_user_policy"
    resource.change.actions[_] != "delete"
    msg := {
        "resource": resource.address,
        "message": "Inline IAM user policies are not allowed; use managed policies with aws_iam_policy + attachment",
        "severity": "high",
    }
}

violations[msg] {
    resource := input.plan.resource_changes[_]
    resource.type == "aws_iam_role_policy"
    resource.change.actions[_] != "delete"
    msg := {
        "resource": resource.address,
        "message": "Inline IAM role policies are not allowed; use managed policies with aws_iam_policy + attachment",
        "severity": "high",
    }
}
