"""Dataclasses and parsing utilities for the AI Template Studio.

Shared between ai-template-studio.py and ai-studio-routes.py.
Generates Jinja2 template packages (main.tf.j2, variables.json, metadata.json).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Tags used by Claude to delimit each generated file
_FILE_TAG_RE = re.compile(
    r"<file name=[\"']([^\"']+)[\"']>(.*?)</file>",
    re.DOTALL,
)

# Required files in a complete Jinja2 template package
REQUIRED_TEMPLATE_FILES = ("main.tf.j2", "variables.json", "metadata.json")


@dataclass
class GeneratedTemplate:
    """A complete Jinja2 template package produced by the AI."""
    name: str                                   # e.g. "hybrid/wireguard-vpn"
    providers: list[str]                        # e.g. ["aws", "proxmox"]
    description: str
    files: dict[str, str] = field(default_factory=dict)   # filename -> content
    display_name: str = ""
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"


@dataclass
class TemplateValidationResult:
    """Result of validating a generated template's Jinja2 syntax and structure."""
    valid: bool
    jinja2_errors: list[str] = field(default_factory=list)
    hcl_errors: dict[str, list[str]] = field(default_factory=dict)
    structure_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_template_files(raw_text: str) -> dict[str, str]:
    """Extract file contents from Claude's <file name="...">...</file> tagged response.

    Falls back to splitting on ### headings if no tags found.
    """
    matches = _FILE_TAG_RE.findall(raw_text)
    if matches:
        return {name.strip(): content.strip() for name, content in matches}

    # Fallback: look for ### filename headings followed by code blocks
    files: dict[str, str] = {}
    sections = re.split(r"###\s+([\w\-./]+\.(?:j2|json|sh|py))", raw_text)
    for i in range(1, len(sections) - 1, 2):
        fname = sections[i].strip()
        body = sections[i + 1]
        body = re.sub(r"```(?:hcl|json|terraform|bash|python)?\n?", "", body)
        body = re.sub(r"```", "", body)
        files[fname] = body.strip()
    return files


def parse_variables_json(raw_text: str) -> list[dict]:
    """Extract variables list from a variables.json string.

    Accepts both {"variables": [...]} and bare [...] formats.
    Returns empty list on parse failure.
    """
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return []

    if isinstance(data, dict):
        return data.get("variables", [])
    if isinstance(data, list):
        return data
    return []


def parse_metadata_json(raw_text: str) -> dict:
    """Extract metadata dict from a metadata.json string.

    Returns empty dict on parse failure.
    """
    try:
        data = json.loads(raw_text)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def validate_jinja2_syntax(content: str) -> list[str]:
    """Try to parse Jinja2 content and return list of syntax errors.

    Returns empty list if syntax is valid.
    """
    from jinja2 import Environment, TemplateSyntaxError
    env = Environment()
    errors: list[str] = []
    try:
        env.parse(content)
    except TemplateSyntaxError as exc:
        errors.append(f"Line {exc.lineno}: {exc.message}")
    return errors


def validate_template_structure(files: dict[str, str]) -> list[str]:
    """Check that required template files are present. Returns list of warnings."""
    warnings: list[str] = []
    for required in REQUIRED_TEMPLATE_FILES:
        if required not in files:
            warnings.append(f"Missing required file: {required}")
    if "main.tf.j2" in files and not files["main.tf.j2"].strip():
        warnings.append("main.tf.j2 is empty — template has no HCL content.")
    if "variables.json" in files:
        parsed = parse_variables_json(files["variables.json"])
        if not parsed:
            warnings.append("variables.json has no variables defined.")
    return warnings
