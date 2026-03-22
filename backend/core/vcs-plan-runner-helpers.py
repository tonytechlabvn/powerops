"""Helper utilities for VCS plan runner (Phase 4).

Provides:
  match_trigger_pattern   — glob branch matching against trigger_patterns list
  format_pr_comment_body  — rich markdown for PR plan comment
  parse_plan_summary      — extract adds/changes/destroys from plan output
  sanitize_plan_output    — strip secrets from plan text before posting to GitHub
"""
from __future__ import annotations

import fnmatch
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that look like secret values — redact before posting to GitHub
_SECRET_PATTERNS = [
    re.compile(r'(?i)(password|secret|token|key|credential)\s*=\s*"[^"]{4,}"'),
    re.compile(r'(?i)(AWS_SECRET|AZURE_CLIENT_SECRET|GOOGLE_CREDENTIALS)\s*=\s*\S+'),
]


def match_trigger_pattern(branch: str, trigger_patterns: list[dict]) -> str | None:
    """Return the action ('plan' | 'apply') for the first matching pattern, or None.

    Patterns are evaluated in order; first match wins.
    Supports glob syntax: 'feature/*' matches 'feature/foo'.
    """
    for pattern in trigger_patterns:
        pat_branch = pattern.get("branch", "")
        action = pattern.get("action", "plan")
        if fnmatch.fnmatch(branch, pat_branch):
            logger.debug("Branch '%s' matched pattern '%s' -> action '%s'", branch, pat_branch, action)
            return action
    return None


def sanitize_plan_output(raw_output: str) -> str:
    """Redact potential secrets from plan output before posting to GitHub."""
    sanitized = raw_output
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(lambda m: m.group(0).split("=")[0] + '= "[REDACTED]"', sanitized)
    return sanitized


def parse_plan_summary(plan_output: str) -> dict[str, int]:
    """Extract resource change counts from terraform plan text output.

    Returns dict with keys: adds, changes, destroys.
    """
    adds = changes = destroys = 0
    # Match: "Plan: 2 to add, 1 to change, 0 to destroy."
    match = re.search(
        r"Plan:\s+(\d+)\s+to add,\s+(\d+)\s+to change,\s+(\d+)\s+to destroy",
        plan_output,
    )
    if match:
        adds, changes, destroys = int(match.group(1)), int(match.group(2)), int(match.group(3))
    else:
        # Fallback: count individual action lines
        adds = len(re.findall(r"^\s+\+\s", plan_output, re.MULTILINE))
        changes = len(re.findall(r"^\s+~\s", plan_output, re.MULTILINE))
        destroys = len(re.findall(r"^\s+-\s", plan_output, re.MULTILINE))
    return {"adds": adds, "changes": changes, "destroys": destroys}


def format_pr_comment_body(
    commit_sha: str,
    branch: str,
    workspace_name: str,
    plan_output: str,
    status: str,
    powerops_url: str,
    policy_passed: bool | None = None,
) -> str:
    """Build rich markdown body for the GitHub PR plan comment."""
    summary = parse_plan_summary(plan_output)
    safe_output = sanitize_plan_output(plan_output)

    # Status badge
    if status == "completed":
        status_badge = "**Plan passed**"
        icon = "✅"
    elif status == "failed":
        status_badge = "**Plan failed**"
        icon = "❌"
    else:
        status_badge = "**Plan running...**"
        icon = "⏳"

    # Policy result
    policy_line = ""
    if policy_passed is not None:
        policy_icon = "✅" if policy_passed else "❌"
        policy_line = f"\n**Policy check:** {policy_icon} {'Passed' if policy_passed else 'Failed'}"

    # Resource change table
    change_table = (
        f"| Resource changes | Count |\n"
        f"|---|---|\n"
        f"| + to add | {summary['adds']} |\n"
        f"| ~ to change | {summary['changes']} |\n"
        f"| - to destroy | {summary['destroys']} |"
    )

    # Truncate large plan output for readability
    output_preview = safe_output[:3000] + ("\n...(truncated)" if len(safe_output) > 3000 else "")

    return (
        f"<!-- powerops-bot -->\n"
        f"## {icon} TerraBot Plan — `{commit_sha[:8]}` on `{branch}`\n\n"
        f"**Workspace:** `{workspace_name}`  {status_badge}{policy_line}\n\n"
        f"{change_table}\n\n"
        f"<details><summary>Full plan output</summary>\n\n"
        f"```hcl\n{output_preview}\n```\n\n</details>\n\n"
        f"[View in PowerOps]({powerops_url})"
    )


def build_plan_summary_json(plan_output: str) -> str:
    """Serialize plan summary dict to JSON string for DB storage."""
    return json.dumps(parse_plan_summary(plan_output))


def extract_resource_changes(plan_output: str) -> list[dict[str, Any]]:
    """Parse individual resource change lines from plan output."""
    changes: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^\s+(?P<symbol>[+~\-<>])\s+(?:resource\s+)?\"?(?P<type>\S+)\"?\s+\"?(?P<name>\S+)\"?",
        re.MULTILINE,
    )
    action_map = {"+": "create", "~": "update", "-": "delete", "<": "read", ">": "replace"}
    for m in pattern.finditer(plan_output):
        symbol = m.group("symbol")
        changes.append({
            "action": action_map.get(symbol, "unknown"),
            "type": m.group("type"),
            "name": m.group("name"),
        })
    return changes
