"""Dataclasses for HCL file manager operations.

Shared data structures used by HCLFileManager and the route layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileInfo:
    """Metadata for a single file or directory entry."""

    path: str           # relative to workspace root (forward slashes)
    name: str           # filename only
    size: int           # bytes (0 for directories)
    modified_at: str    # ISO 8601
    is_directory: bool
    checksum: str       # sha256 hex of content (empty for directories)


@dataclass
class FileContent:
    """Content and metadata of a readable file."""

    path: str
    content: str
    checksum: str   # sha256 hex
    size: int
    language: str   # "hcl" | "json" | "yaml" | "text" | etc.


@dataclass
class WriteResult:
    """Result of a write_file operation."""

    path: str
    checksum: str
    validation: ValidationSummary | None = None


@dataclass
class SearchResult:
    """Single line match from a file content search."""

    path: str
    line: int
    content: str        # the matching line text
    context_before: str = ""
    context_after: str  = ""


@dataclass
class ValidationSummary:
    """Lightweight HCL validation outcome (no full resource list)."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Map file extensions to language identifiers for Monaco Editor
_EXT_LANGUAGE: dict[str, str] = {
    ".tf":      "hcl",
    ".tfvars":  "hcl",
    ".hcl":     "hcl",
    ".json":    "json",
    ".yaml":    "yaml",
    ".yml":     "yaml",
    ".sh":      "shell",
    ".md":      "markdown",
}


def detect_language(filename: str) -> str:
    """Return Monaco language ID from filename extension."""
    from pathlib import Path
    return _EXT_LANGUAGE.get(Path(filename).suffix.lower(), "text")
