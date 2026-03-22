"""Parse Terraform module archives (zip) to extract metadata.

Reads variables.tf, outputs.tf, main.tf (and other .tf files) from a zip
archive. Uses python-hcl2 when available; falls back to regex extraction.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try to import python-hcl2 — optional dependency
try:
    import hcl2  # type: ignore[import-untyped]
    _HCL2_AVAILABLE = True
except ImportError:
    _HCL2_AVAILABLE = False
    logger.warning("python-hcl2 not installed — falling back to regex HCL parsing")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def checksum_bytes(data: bytes) -> str:
    """Return SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def validate_archive(archive_bytes: bytes, max_bytes: int = 50 * 1024 * 1024) -> None:
    """Raise ValueError for oversized, corrupt, or unsafe archives."""
    if len(archive_bytes) > max_bytes:
        raise ValueError(f"Archive exceeds {max_bytes // (1024*1024)} MB limit")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
            for info in zf.infolist():
                # Block path traversal
                if ".." in info.filename or info.filename.startswith("/"):
                    raise ValueError(f"Unsafe path in archive: {info.filename}")
                # Block symlinks (external_attr encodes file type in high bits)
                if (info.external_attr >> 16) & 0xA000 == 0xA000:
                    raise ValueError(f"Symlinks not allowed: {info.filename}")
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid zip archive: {exc}") from exc


# ---------------------------------------------------------------------------
# HCL extraction
# ---------------------------------------------------------------------------

def extract_readme(zip_path: Path) -> str:
    """Read README.md from the root of the zip archive."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            for candidate in ("README.md", "readme.md", "Readme.md"):
                if candidate in names:
                    return zf.read(candidate).decode("utf-8", errors="replace")
            # Also check one level deep (e.g. module-name/README.md)
            for name in names:
                if name.lower().endswith("readme.md") and name.count("/") == 1:
                    return zf.read(name).decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read README from archive: %s", exc)
    return ""


def extract_variables(zip_path: Path) -> list[dict[str, Any]]:
    """Extract variable blocks from variables.tf (or any .tf file)."""
    content = _read_tf_file(zip_path, "variables.tf")
    if not content:
        # Scan all .tf files for variable blocks
        content = _concat_tf_files(zip_path)
    return _parse_variables(content)


def extract_outputs(zip_path: Path) -> list[dict[str, Any]]:
    """Extract output blocks from outputs.tf (or any .tf file)."""
    content = _read_tf_file(zip_path, "outputs.tf")
    if not content:
        content = _concat_tf_files(zip_path)
    return _parse_outputs(content)


def extract_resources(zip_path: Path) -> list[dict[str, Any]]:
    """Extract resource blocks from all .tf files."""
    content = _concat_tf_files(zip_path)
    return _parse_resources(content)


def generate_usage_example(module_address: str, variables: list[dict[str, Any]]) -> str:
    """Generate HCL usage snippet from required variables."""
    lines = [f'module "example" {{', f'  source  = "{module_address}"', ""]
    required = [v for v in variables if v.get("required", False)]
    optional = [v for v in variables if not v.get("required", False)]
    for v in required:
        lines.append(f'  {v["name"]} = "<required>"  # {v.get("description", "").strip()}')
    if required and optional:
        lines.append("")
    for v in optional[:5]:  # Show first 5 optional vars
        default = v.get("default", "null")
        lines.append(f'  # {v["name"]} = {json.dumps(default)}')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_tf_file(zip_path: Path, filename: str) -> str:
    """Read a specific .tf file from the archive root or one level deep."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            if filename in names:
                return zf.read(filename).decode("utf-8", errors="replace")
            # Try one directory deep
            for name in names:
                parts = name.split("/")
                if len(parts) == 2 and parts[1] == filename:
                    return zf.read(name).decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s from archive: %s", filename, exc)
    return ""


def _concat_tf_files(zip_path: Path) -> str:
    """Concatenate all .tf files from archive into one string."""
    parts: list[str] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.endswith(".tf") and name.count("/") <= 1:
                    parts.append(zf.read(name).decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.warning("Failed to read .tf files from archive: %s", exc)
    return "\n".join(parts)


def _parse_variables(content: str) -> list[dict[str, Any]]:
    if _HCL2_AVAILABLE and content:
        try:
            parsed = hcl2.loads(content)
            return _hcl2_variables(parsed)
        except Exception:
            pass
    return _regex_variables(content)


def _parse_outputs(content: str) -> list[dict[str, Any]]:
    if _HCL2_AVAILABLE and content:
        try:
            parsed = hcl2.loads(content)
            return _hcl2_outputs(parsed)
        except Exception:
            pass
    return _regex_outputs(content)


def _parse_resources(content: str) -> list[dict[str, Any]]:
    return _regex_resources(content)


def _hcl2_variables(parsed: dict) -> list[dict[str, Any]]:
    results = []
    for var_block in parsed.get("variable", []):
        for name, attrs in var_block.items():
            results.append({
                "name": name,
                "type": str(attrs.get("type", "any")),
                "description": attrs.get("description", ""),
                "default": attrs.get("default"),
                "required": "default" not in attrs,
                "validation": str(attrs.get("validation", {}).get("condition", "")) or None,
            })
    return results


def _hcl2_outputs(parsed: dict) -> list[dict[str, Any]]:
    results = []
    for out_block in parsed.get("output", []):
        for name, attrs in out_block.items():
            results.append({
                "name": name,
                "description": attrs.get("description", ""),
                "value": str(attrs.get("value", "")),
            })
    return results


def _regex_variables(content: str) -> list[dict[str, Any]]:
    results = []
    for m in re.finditer(r'variable\s+"(\w+)"\s*\{([^}]*)\}', content, re.DOTALL):
        name, body = m.group(1), m.group(2)
        desc = re.search(r'description\s*=\s*"([^"]*)"', body)
        default = re.search(r'default\s*=\s*(.+)', body)
        vtype = re.search(r'type\s*=\s*(\S+)', body)
        results.append({
            "name": name,
            "type": vtype.group(1) if vtype else "any",
            "description": desc.group(1) if desc else "",
            "default": default.group(1).strip() if default else None,
            "required": default is None,
            "validation": None,
        })
    return results


def _regex_outputs(content: str) -> list[dict[str, Any]]:
    results = []
    for m in re.finditer(r'output\s+"(\w+)"\s*\{([^}]*)\}', content, re.DOTALL):
        name, body = m.group(1), m.group(2)
        desc = re.search(r'description\s*=\s*"([^"]*)"', body)
        value = re.search(r'value\s*=\s*(.+)', body)
        results.append({
            "name": name,
            "description": desc.group(1) if desc else "",
            "value": value.group(1).strip() if value else "",
        })
    return results


def _regex_resources(content: str) -> list[dict[str, Any]]:
    results = []
    for m in re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"', content):
        rtype = m.group(1)
        rname = m.group(2)
        provider = rtype.split("_")[0] if "_" in rtype else rtype
        results.append({"type": rtype, "name": rname, "provider": provider})
    return results
