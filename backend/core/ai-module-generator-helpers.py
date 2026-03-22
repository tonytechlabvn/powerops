"""Dataclasses for the AI module generator (Phase 11).

Shared between ai-module-generator.py and module-generator-routes.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Expected files in a complete Terraform module
REQUIRED_MODULE_FILES = ("main.tf", "variables.tf", "outputs.tf")
OPTIONAL_MODULE_FILES = ("README.md", "versions.tf")

# Tags used by Claude to delimit each generated file
_FILE_TAG_RE = re.compile(
    r"<file name=[\"']([^\"']+)[\"']>(.*?)</file>",
    re.DOTALL,
)


@dataclass
class GeneratedModule:
    """A complete Terraform module produced by the AI."""
    name: str
    provider: str
    description: str
    files: dict[str, str] = field(default_factory=dict)   # filename -> content
    variables: list[dict] = field(default_factory=list)   # parsed variable blocks
    outputs: list[dict] = field(default_factory=list)     # parsed output blocks
    resources: list[str] = field(default_factory=list)    # resource addresses


@dataclass
class ModuleGenerationEvent:
    """Streaming progress event for module generation."""
    type: str          # "file_start" | "file_content" | "file_complete" | "done" | "error"
    file_name: str | None = None
    content: str | None = None


@dataclass
class ModuleValidationResult:
    """Result of validating a generated module's HCL files and structure."""
    valid: bool
    file_errors: dict[str, list[str]] = field(default_factory=dict)
    structure_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_module_files(raw_text: str) -> dict[str, str]:
    """Extract file contents from Claude's <file name="...">...</file> tagged response.

    Falls back to splitting on common filename markers if no tags found.
    """
    matches = _FILE_TAG_RE.findall(raw_text)
    if matches:
        return {name.strip(): content.strip() for name, content in matches}

    # Fallback: look for ### filename.tf headings followed by code blocks
    files: dict[str, str] = {}
    sections = re.split(r"###\s+([\w\-]+\.(?:tf|md))", raw_text)
    for i in range(1, len(sections) - 1, 2):
        fname = sections[i].strip()
        body = sections[i + 1]
        # Strip markdown code fences
        body = re.sub(r"```(?:hcl|terraform|markdown)?\n?", "", body)
        body = re.sub(r"```", "", body)
        files[fname] = body.strip()
    return files


def validate_module_structure(files: dict[str, str]) -> list[str]:
    """Check that required module files are present. Returns list of warnings."""
    warnings: list[str] = []
    for required in REQUIRED_MODULE_FILES:
        if required not in files:
            warnings.append(f"Missing required file: {required}")
    if "variables.tf" in files and not files["variables.tf"].strip():
        warnings.append("variables.tf is empty — consider adding input variables.")
    if "outputs.tf" in files and not files["outputs.tf"].strip():
        warnings.append("outputs.tf is empty — modules should expose key outputs.")
    return warnings
