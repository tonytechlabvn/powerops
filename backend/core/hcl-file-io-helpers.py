"""Low-level I/O helpers for HCLFileManager: checksum, language detection, HCL validation.

Extracted from hcl-file-manager.py to keep file sizes under 200 lines.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 1024 * 1024  # 1 MiB


def sha256(text: str) -> str:
    """Return hex SHA-256 digest of UTF-8 encoded *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iso_timestamp(ts: float) -> str:
    """Convert a POSIX timestamp to an ISO 8601 UTC string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def load_helpers_module():
    """Lazily load hcl-file-manager-helpers (dataclasses)."""
    import importlib.util as ilu
    import sys
    alias = "backend.core.hcl_file_manager_helpers"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = ilu.spec_from_file_location(alias, Path(__file__).parent / "hcl-file-manager-helpers.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def validate_hcl_content(content: str) -> object:
    """Run hcl-validator.validate_syntax and return a ValidationSummary dataclass."""
    h = load_helpers_module()
    try:
        from backend.core import hcl_validator
        result = hcl_validator.validate_syntax(content)
        return h.ValidationSummary(valid=result.valid, errors=result.errors)
    except Exception as exc:
        logger.warning("HCL validation error: %s", exc)
        return h.ValidationSummary(valid=False, errors=[str(exc)])


def build_file_info(p: Path, root: Path) -> object:
    """Build a FileInfo dataclass from a resolved Path within *root*."""
    h = load_helpers_module()
    try:
        stat = p.stat()
    except OSError:
        return None
    rel = p.relative_to(root).as_posix()
    checksum = sha256(p.read_text("utf-8", errors="replace")) if p.is_file() else ""
    return h.FileInfo(
        path=rel,
        name=p.name,
        size=stat.st_size,
        modified_at=iso_timestamp(stat.st_mtime),
        is_directory=p.is_dir(),
        checksum=checksum,
    )
