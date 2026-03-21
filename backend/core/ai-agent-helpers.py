"""Private helper utilities for the TerraBot AI agent.

Extracted from ai-agent.py to keep that file under 200 lines.
Not intended for direct use outside of ai-agent.py.
"""
from __future__ import annotations

import re

import anthropic

# Regex to extract HCL from <terraform>...</terraform> tags (non-greedy, dotall)
_HCL_TAG_RE = re.compile(r"<terraform>(.*?)</terraform>", re.DOTALL)

# Maps confidence keywords in Claude's response to float scores
_CONFIDENCE_MAP = {"high": 0.9, "medium": 0.6, "low": 0.3}


def extract_hcl(text: str) -> str:
    """Pull HCL content from <terraform> tags. Returns empty string if not found."""
    match = _HCL_TAG_RE.search(text)
    return match.group(1).strip() if match else ""


def extract_explanation(text: str) -> str:
    """Extract plain-English text that follows the closing </terraform> tag."""
    tag = "</terraform>"
    idx = text.find(tag)
    if idx == -1:
        return ""
    return text[idx + len(tag):].strip()


def extract_section(text: str, heading: str) -> str:
    """Extract content under a markdown ### heading, up to the next heading or end."""
    pattern = re.compile(
        rf"###\s+{re.escape(heading)}\s*\n(.*?)(?=###|\Z)", re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def extract_tagged_lines(text: str, *tags: str) -> list[str]:
    """Collect lines whose stripped content starts with any of the given tag prefixes."""
    results: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.upper().startswith(t.upper()) for t in tags):
            results.append(stripped)
    return results


def parse_confidence(text: str) -> float:
    """Extract a 0.0–1.0 confidence score from a diagnosis response.

    Looks for 'Confidence: High/Medium/Low' in the response text.
    Falls back to 0.5 (medium) if the pattern is not found.
    """
    lower = text.lower()
    for keyword, value in _CONFIDENCE_MAP.items():
        if f"confidence: {keyword}" in lower or f"confidence\n{keyword}" in lower:
            return value
    return 0.5


def log_usage(logger, operation: str, usage: anthropic.types.Usage) -> None:
    """Log Claude token usage at INFO level for a named operation."""
    logger.info(
        "Claude usage [%s]: input=%d output=%d tokens",
        operation,
        usage.input_tokens,
        usage.output_tokens,
    )
