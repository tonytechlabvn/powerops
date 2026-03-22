"""HCL file manager — sandboxed filesystem CRUD for workspace .tf files.

Security-critical: every path is resolved and verified to be a strict
descendant of the workspace root before any I/O operation.

Low-level helpers (checksum, language detection, HCL validation) live in
hcl-file-io-helpers.py. Dataclasses live in hcl-file-manager-helpers.py.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _io():
    """Lazily load hcl-file-io-helpers module."""
    import importlib.util as ilu, sys
    alias = "backend.core.hcl_file_io_helpers"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = ilu.spec_from_file_location(alias, Path(__file__).parent / "hcl-file-io-helpers.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class HCLFileManager:
    """Sandboxed filesystem operations within a single workspace directory."""

    def __init__(self, workspace_dir: Path) -> None:
        self._root = workspace_dir.resolve()

    # ------------------------------------------------------------------
    # Security: path validation
    # ------------------------------------------------------------------

    def _safe_path(self, relative: str) -> Path:
        """Resolve *relative* inside workspace root; raise on traversal/symlink escape."""
        if not relative or relative.strip() == "":
            raise ValueError("File path must not be empty.")
        if Path(relative).is_absolute():
            raise ValueError("Absolute paths are not allowed.")
        candidate = (self._root / relative).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError:
            raise ValueError(f"Path traversal detected: '{relative}' escapes workspace root.")
        if candidate.is_symlink():
            try:
                candidate.resolve().relative_to(self._root)
            except ValueError:
                raise ValueError(f"Symlink '{relative}' points outside workspace root.")
        return candidate

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    async def list_files(self, pattern: str = "**/*.tf") -> list:
        """Return FileInfo list for all files matching *pattern*, skipping .terraform/."""
        io = _io()
        results = []
        for p in sorted(self._root.rglob(pattern.lstrip("/"))):
            if ".terraform" in p.parts:
                continue
            fi = io.build_file_info(p, self._root)
            if fi is not None:
                results.append(fi)
        return results

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    async def read_file(self, relative: str):
        """Read file content; return FileContent with checksum and language."""
        io = _io()
        h = io.load_helpers_module()
        path = self._safe_path(relative)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {relative}")
        if not path.is_file():
            raise IsADirectoryError(f"Path is a directory: {relative}")
        size = path.stat().st_size
        if size > io.MAX_FILE_SIZE:
            raise ValueError(f"File exceeds 1 MiB limit: {relative} ({size} bytes)")
        content = path.read_text("utf-8")
        return h.FileContent(
            path=relative, content=content,
            checksum=io.sha256(content), size=size,
            language=h.detect_language(path.name),
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    async def write_file(self, relative: str, content: str,
                         expected_checksum: str | None = None):
        """Write *content* to *relative*.

        Raises ValueError on checksum conflict (optimistic locking) or size excess.
        Returns WriteResult with optional HCL ValidationSummary for .tf files.
        """
        io = _io()
        h = io.load_helpers_module()
        path = self._safe_path(relative)

        if expected_checksum and path.exists():
            current = io.sha256(path.read_text("utf-8"))
            if current != expected_checksum:
                raise ValueError(
                    "Checksum mismatch — file was modified by another session. "
                    "Reload and retry."
                )

        encoded = content.encode("utf-8")
        if len(encoded) > io.MAX_FILE_SIZE:
            raise ValueError(f"Content exceeds 1 MiB limit ({len(encoded)} bytes).")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        checksum = io.sha256(content)

        validation = io.validate_hcl_content(content) if path.suffix == ".tf" else None
        logger.debug("Wrote file: %s (%d bytes)", relative, len(encoded))
        return h.WriteResult(path=relative, checksum=checksum, validation=validation)

    # ------------------------------------------------------------------
    # Delete / rename
    # ------------------------------------------------------------------

    async def delete_file(self, relative: str) -> None:
        path = self._safe_path(relative)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {relative}")
        if not path.is_file():
            raise IsADirectoryError(f"Use delete_directory for directories: {relative}")
        path.unlink()

    async def rename_file(self, old_path: str, new_path: str) -> None:
        src = self._safe_path(old_path)
        dst = self._safe_path(new_path)
        if not src.exists():
            raise FileNotFoundError(f"Source not found: {old_path}")
        if dst.exists():
            raise FileExistsError(f"Destination already exists: {new_path}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)

    # ------------------------------------------------------------------
    # Directory operations
    # ------------------------------------------------------------------

    async def create_directory(self, relative: str) -> None:
        self._safe_path(relative).mkdir(parents=True, exist_ok=True)

    async def delete_directory(self, relative: str) -> None:
        path = self._safe_path(relative)
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {relative}")
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {relative}")
        shutil.rmtree(path)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_files(self, query: str, pattern: str = "**/*.tf") -> list:
        """Case-insensitive substring search across workspace files."""
        io = _io()
        h = io.load_helpers_module()
        results = []
        q = query.lower()
        for p in sorted(self._root.rglob(pattern.lstrip("/"))):
            if ".terraform" in p.parts or not p.is_file():
                continue
            try:
                lines = p.read_text("utf-8", errors="replace").splitlines()
            except OSError:
                continue
            rel = p.relative_to(self._root).as_posix()
            for idx, line in enumerate(lines, start=1):
                if q in line.lower():
                    results.append(h.SearchResult(
                        path=rel, line=idx, content=line,
                        context_before=lines[idx - 2] if idx > 1 else "",
                        context_after=lines[idx] if idx < len(lines) else "",
                    ))
        return results
