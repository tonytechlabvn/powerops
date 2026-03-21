"""Workspace manager — multi-workspace lifecycle management.

Wraps `terraform workspace` commands and persists workspace metadata
in the database (Workspace ORM model).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
import sys as _sys

logger = logging.getLogger(__name__)


def _load_sibling(filename: str, alias: str):
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, Path(__file__).parent / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_subprocess_executor = _load_sibling("subprocess-executor.py", "subprocess_executor")
run_process = _subprocess_executor.run_process


class WorkspaceManager:
    """Manage Terraform workspaces with persistent metadata.

    Args:
        base_dir: Root directory under which workspace dirs are created.
        binary:   Path to the terraform executable.
        timeout:  Per-command timeout in seconds.
    """

    def __init__(
        self,
        base_dir: Path | str = "./workspaces",
        binary: str = "terraform",
        timeout: int = 300,
    ):
        self.base_dir = Path(base_dir).resolve()
        self.binary = binary
        self.timeout = timeout
        self._env = dict(os.environ)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _workspace_dir(self, name: str) -> Path:
        return self.base_dir / name

    async def _tf_run(self, *args: str, cwd: Path | None = None) -> tuple[str, str, int]:
        """Run terraform command; return (stdout, stderr, returncode)."""
        cmd = [self.binary, *args]
        work_cwd = cwd or self.base_dir
        result = await run_process(cmd, work_cwd, self._env, self.timeout)
        return result.stdout, result.stderr, result.return_code

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, name: str, provider: str = "", environment: str = "") -> dict:
        """Create a workspace directory and register it in the database.

        Returns a dict matching the Workspace ORM row fields.
        """
        ws_dir = self._workspace_dir(name)
        ws_dir.mkdir(parents=True, exist_ok=True)

        # Write a minimal workspace metadata file
        meta_path = ws_dir / ".terrabot-meta.json"
        meta = {
            "name": name,
            "provider": provider,
            "environment": environment,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": datetime.utcnow().isoformat(),
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        # Persist to DB
        await self._upsert_db(name, provider, environment, ws_dir)

        logger.info("Workspace created: %s", name)
        return {
            "name": name,
            "provider": provider,
            "environment": environment,
            "workspace_dir": str(ws_dir),
            "created_at": meta["created_at"],
            "last_used": meta["last_used"],
        }

    async def switch(self, name: str) -> dict:
        """Switch to a workspace by name; returns updated workspace dict."""
        ws_dir = self._workspace_dir(name)
        if not ws_dir.exists():
            raise ValueError(f"Workspace not found: {name}")

        stdout, stderr, rc = await self._tf_run(
            "workspace", "select", "-or-create", name, cwd=ws_dir
        )
        if rc != 0:
            raise RuntimeError(f"terraform workspace select failed: {stderr.strip()}")

        await self._touch_last_used(name)
        logger.info("Switched to workspace: %s", name)
        return await self._load_meta(ws_dir)

    async def list_workspaces(self) -> list[dict]:
        """Return all workspaces from the database, or scan base_dir."""
        from backend.db.database import get_session
        from backend.db.models import Workspace as WSModel

        try:
            from sqlalchemy import select as sa_select
            async with get_session() as session:
                rows = (await session.execute(sa_select(WSModel))).scalars().all()
                return [
                    {
                        "name": r.name,
                        "provider": r.provider,
                        "environment": r.environment,
                        "workspace_dir": r.workspace_dir,
                        "created_at": r.created_at.isoformat() if r.created_at else "",
                        "last_used": r.last_used.isoformat() if r.last_used else "",
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning("DB list failed, falling back to filesystem scan: %s", exc)
            return await self._fs_list()

    async def delete(self, name: str) -> bool:
        """Delete a workspace directory and remove DB record."""
        import shutil

        ws_dir = self._workspace_dir(name)
        if ws_dir.exists():
            shutil.rmtree(ws_dir)

        # Remove DB row
        try:
            from backend.db.database import get_session
            from backend.db.models import Workspace as WSModel
            from sqlalchemy import delete as sa_delete
            async with get_session() as session:
                await session.execute(sa_delete(WSModel).where(WSModel.name == name))
        except Exception as exc:
            logger.warning("DB delete failed for workspace %s: %s", name, exc)

        logger.info("Workspace deleted: %s", name)
        return True

    async def get_current(self) -> dict:
        """Return the currently selected workspace dict (reads .terraform state)."""
        tf_env_file = self.base_dir / ".terraform" / "environment"
        if tf_env_file.exists():
            current_name = tf_env_file.read_text().strip()
        else:
            current_name = "default"

        ws_dir = self._workspace_dir(current_name)
        if ws_dir.exists():
            return await self._load_meta(ws_dir)
        return {"name": current_name, "provider": "", "environment": "", "workspace_dir": str(ws_dir)}

    async def get_state_summary(self, name: str) -> dict:
        """Run `terraform show -json` in workspace dir and return a summary."""
        ws_dir = self._workspace_dir(name)
        if not ws_dir.exists():
            raise ValueError(f"Workspace not found: {name}")

        stdout, stderr, rc = await self._tf_run("show", "-json", "-no-color", cwd=ws_dir)
        if rc != 0:
            return {"name": name, "resource_count": 0, "error": stderr.strip()}

        try:
            state = json.loads(stdout)
        except json.JSONDecodeError:
            return {"name": name, "resource_count": 0, "error": "invalid JSON from terraform show"}

        resources = state.get("values", {}).get("root_module", {}).get("resources", [])
        return {
            "name": name,
            "resource_count": len(resources),
            "resources": [
                {"address": r.get("address"), "type": r.get("type"), "name": r.get("name")}
                for r in resources
            ],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _upsert_db(self, name: str, provider: str, environment: str, ws_dir: Path) -> None:
        """Insert or update workspace row in DB (best-effort)."""
        try:
            from backend.db.database import get_session
            from backend.db.models import Workspace as WSModel
            from sqlalchemy import select as sa_select

            async with get_session() as session:
                existing = (
                    await session.execute(sa_select(WSModel).where(WSModel.name == name))
                ).scalar_one_or_none()

                if existing:
                    existing.provider = provider
                    existing.environment = environment
                    existing.last_used = datetime.utcnow()
                    session.add(existing)
                else:
                    session.add(
                        WSModel(
                            name=name,
                            provider=provider,
                            environment=environment,
                            workspace_dir=str(ws_dir),
                        )
                    )
        except Exception as exc:
            logger.warning("DB upsert failed for workspace %s: %s", name, exc)

    async def _touch_last_used(self, name: str) -> None:
        try:
            from backend.db.database import get_session
            from backend.db.models import Workspace as WSModel
            from sqlalchemy import select as sa_select

            async with get_session() as session:
                row = (
                    await session.execute(sa_select(WSModel).where(WSModel.name == name))
                ).scalar_one_or_none()
                if row:
                    row.last_used = datetime.utcnow()
                    session.add(row)
        except Exception as exc:
            logger.debug("Could not touch last_used for %s: %s", name, exc)

    async def _load_meta(self, ws_dir: Path) -> dict:
        meta_path = ws_dir / ".terrabot-meta.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                pass
        return {"name": ws_dir.name, "provider": "", "environment": "", "workspace_dir": str(ws_dir)}

    async def _fs_list(self) -> list[dict]:
        if not self.base_dir.exists():
            return []
        result = []
        for entry in self.base_dir.iterdir():
            if entry.is_dir():
                result.append(await self._load_meta(entry))
        return result
