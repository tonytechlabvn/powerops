"""Dataclasses for the AI remediation engine (Phase 10).

Shared between ai-remediation-engine.py and remediation-routes.py.
Kept separate to avoid circular imports and stay under 200-line limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ErrorCategory:
    """Classification of a terraform error by type and fixability."""
    type: str           # "hcl_syntax" | "missing_attribute" | "invalid_resource"
                        # | "permission" | "state" | "provider" | "unknown"
    is_code_fixable: bool
    severity: str       # "error" | "warning"


@dataclass
class FileFix:
    """A suggested fix for a single workspace file."""
    file_path: str
    original_content: str
    fixed_content: str
    diff_lines: list[str]    # unified diff lines
    description: str         # human-readable description of the fix


@dataclass
class RemediationResult:
    """Full result of a diagnose-and-fix cycle."""
    error_category: ErrorCategory
    root_cause: str
    is_fixable: bool
    fixes: list[FileFix] = field(default_factory=list)
    explanation: str = ""
    confidence: float = 0.5


@dataclass
class ApplyFixResult:
    """Result of applying file fixes to the workspace."""
    applied: list[str] = field(default_factory=list)   # successfully updated paths
    failed: list[str] = field(default_factory=list)    # paths that could not be written
    validation_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Classification helpers (deterministic, no AI needed)
# ---------------------------------------------------------------------------

# Keywords that signal each error category
_CATEGORY_PATTERNS: list[tuple[str, str, bool]] = [
    # (keyword_lower, category_type, is_code_fixable)
    ("syntax error",          "hcl_syntax",         True),
    ("unexpected token",      "hcl_syntax",         True),
    ("invalid expression",    "hcl_syntax",         True),
    ("required argument",     "missing_attribute",  True),
    ("missing required",      "missing_attribute",  True),
    ("unsupported argument",  "missing_attribute",  True),
    ("invalid resource type", "invalid_resource",   True),
    ("resource type not",     "invalid_resource",   True),
    ("accessdenied",          "permission",         False),
    ("unauthorized",          "permission",         False),
    ("not authorized",        "permission",         False),
    ("state lock",            "state",              False),
    ("error locking",         "state",              False),
    ("provider produced",     "provider",           False),
    ("provider configuration","provider",           True),
]


def classify_error(error_output: str) -> ErrorCategory:
    """Classify a terraform error string into a structured ErrorCategory.

    Uses keyword matching — fast, deterministic, no API call needed.
    Falls back to 'unknown' when no pattern matches.
    """
    lower = error_output.lower()
    for keyword, category, fixable in _CATEGORY_PATTERNS:
        if keyword in lower:
            return ErrorCategory(
                type=category,
                is_code_fixable=fixable,
                severity="error",
            )
    return ErrorCategory(type="unknown", is_code_fixable=False, severity="error")


def make_unified_diff(original: str, fixed: str, file_path: str) -> list[str]:
    """Generate unified diff lines between original and fixed content."""
    import difflib
    orig_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        orig_lines, fixed_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    ))
    return diff
