"""Drift detector — compare live infrastructure against Terraform state.

Runs `terraform plan -detailed-exitcode` in check mode; any non-zero
change count means drift. Results are persisted as DriftCheck ORM rows.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
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


@dataclass
class DriftReport:
    """Result of a single drift check."""

    workspace: str
    timestamp: str
    has_drift: bool
    drifted_resources: list[dict] = field(default_factory=list)
    error: str = ""
    raw_output: str = ""


class DriftDetector:
    """Detect infrastructure drift for a Terraform workspace.

    Args:
        binary:  Path to the terraform executable.
        timeout: Per-operation timeout in seconds.
    """

    def __init__(self, binary: str = "terraform", timeout: int = 900):
        self.binary = binary
        self.timeout = timeout
        self._env = dict(os.environ)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_drift(self, workspace: str, workspace_dir: str | Path) -> DriftReport:
        """Run terraform plan in check mode and detect drift.

        Exit code 0 = no changes (no drift).
        Exit code 2 = changes present (drift detected).
        Exit code 1 = error.

        Args:
            workspace:     Logical workspace name (used for labelling/DB).
            workspace_dir: Path to the terraform configuration directory.

        Returns:
            DriftReport with drifted_resources list.
        """
        ws_dir = Path(workspace_dir).resolve()
        timestamp = datetime.utcnow().isoformat()

        if not ws_dir.exists():
            report = DriftReport(
                workspace=workspace,
                timestamp=timestamp,
                has_drift=False,
                error=f"Workspace directory not found: {ws_dir}",
            )
            await self._persist(report)
            return report

        cmd = [self.binary, "plan", "-json", "-no-color", "-detailed-exitcode", "-refresh-only"]
        result = await run_process(cmd, ws_dir, self._env, self.timeout)

        if result.return_code == 1 and not result.stdout.strip():
            # Hard error (e.g. backend not initialised)
            report = DriftReport(
                workspace=workspace,
                timestamp=timestamp,
                has_drift=False,
                error=result.stderr.strip() or "terraform plan failed",
                raw_output=result.stdout,
            )
            await self._persist(report)
            return report

        drifted = self._parse_drifted_resources(result.stdout)
        has_drift = result.return_code == 2 or len(drifted) > 0

        report = DriftReport(
            workspace=workspace,
            timestamp=timestamp,
            has_drift=has_drift,
            drifted_resources=drifted,
            raw_output=result.stdout,
        )
        await self._persist(report)
        return report

    async def get_drift_history(self, workspace: str, limit: int = 20) -> list[DriftReport]:
        """Return past drift reports for a workspace from the database.

        Args:
            workspace: Logical workspace name.
            limit:     Maximum records to return (newest first).

        Returns:
            List of DriftReport objects ordered by timestamp descending.
        """
        try:
            from backend.db.database import get_session
            from backend.db.models import DriftCheck
            from sqlalchemy import select as sa_select, desc

            async with get_session() as session:
                rows = (
                    await session.execute(
                        sa_select(DriftCheck)
                        .where(DriftCheck.workspace == workspace)
                        .order_by(desc(DriftCheck.checked_at))
                        .limit(limit)
                    )
                ).scalars().all()

            return [
                DriftReport(
                    workspace=r.workspace,
                    timestamp=r.checked_at.isoformat() if r.checked_at else "",
                    has_drift=r.has_drift,
                    drifted_resources=json.loads(r.drifted_resources_json or "[]"),
                    error=r.error or "",
                )
                for r in rows
            ]
        except Exception as exc:
            logger.warning("Could not fetch drift history: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_drifted_resources(self, stdout: str) -> list[dict]:
        """Parse newline-delimited JSON from `terraform plan -json`."""
        drifted: list[dict] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # resource_drift is emitted by -refresh-only plans
            for rd in obj.get("resource_drift", []):
                change = rd.get("change", {})
                actions = change.get("actions", [])
                if actions and actions != ["no-op"]:
                    drifted.append(
                        {
                            "address": rd.get("address", ""),
                            "type": rd.get("type", ""),
                            "name": rd.get("name", ""),
                            "actions": actions,
                        }
                    )

            # Also catch resource_changes from a regular plan
            for rc in obj.get("resource_changes", []):
                change = rc.get("change", {})
                actions = change.get("actions", [])
                if actions and actions != ["no-op"]:
                    drifted.append(
                        {
                            "address": rc.get("address", ""),
                            "type": rc.get("type", ""),
                            "name": rc.get("name", ""),
                            "actions": actions,
                        }
                    )

        # Deduplicate by address
        seen: set[str] = set()
        unique: list[dict] = []
        for item in drifted:
            if item["address"] not in seen:
                seen.add(item["address"])
                unique.append(item)
        return unique

    async def _persist(self, report: DriftReport) -> None:
        """Save drift report to DB (best-effort; never raises)."""
        try:
            from backend.db.database import get_session
            from backend.db.models import DriftCheck

            async with get_session() as session:
                session.add(
                    DriftCheck(
                        workspace=report.workspace,
                        has_drift=report.has_drift,
                        drifted_resources_json=json.dumps(report.drifted_resources),
                        error=report.error,
                    )
                )
        except Exception as exc:
            logger.warning("Could not persist drift report: %s", exc)
