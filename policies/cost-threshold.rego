package terrabot.policy.cost_threshold

# Default cost threshold in USD; can be overridden via input.config.cost_threshold
default _threshold := 100

_threshold := input.config.cost_threshold {
    input.config.cost_threshold
}

# Warn (not violation) when estimated cost exceeds threshold
warnings[msg] {
    cost := input.run.cost_estimate
    cost > _threshold
    msg := {
        "resource": "run",
        "message": sprintf(
            "Estimated run cost $%.2f exceeds threshold $%.2f — review before applying",
            [cost, _threshold],
        ),
        "severity": "medium",
    }
}
