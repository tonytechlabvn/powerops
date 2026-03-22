"""Variable set workspace assignment operations.

Handles assign/unassign and querying which sets belong to a workspace.
Extracted from variable-set-manager.py to keep file sizes under 200 lines.
"""
from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def _new_id() -> str:
    return str(uuid.uuid4())


def _load_helpers():
    import importlib.util as ilu
    import sys
    from pathlib import Path
    alias = "backend.core.variable_set_encryption_helpers"
    if alias in sys.modules:
        return sys.modules[alias]
    spec = ilu.spec_from_file_location(alias, Path(__file__).parent / "variable-set-encryption-helpers.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class VariableSetAssignmentManager:
    """Manages workspace ↔ variable-set assignment records."""

    async def assign_to_workspace(self, vs_id: str, workspace_id: str,
                                  priority: int = 0) -> None:
        """Attach *vs_id* to *workspace_id*; update priority if already assigned."""
        from backend.db.database import get_session
        from backend.db.models import VariableSetAssignment
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            existing = (await session.execute(
                sa_select(VariableSetAssignment)
                .where(VariableSetAssignment.variable_set_id == vs_id)
                .where(VariableSetAssignment.workspace_id == workspace_id)
            )).scalar_one_or_none()

            if existing:
                existing.priority = priority
                session.add(existing)
            else:
                session.add(VariableSetAssignment(
                    id=_new_id(),
                    variable_set_id=vs_id,
                    workspace_id=workspace_id,
                    priority=priority,
                ))

    async def unassign_from_workspace(self, vs_id: str, workspace_id: str) -> None:
        """Remove assignment of *vs_id* from *workspace_id*."""
        from backend.db.database import get_session
        from backend.db.models import VariableSetAssignment
        from sqlalchemy import delete as sa_delete

        async with get_session() as session:
            await session.execute(
                sa_delete(VariableSetAssignment)
                .where(VariableSetAssignment.variable_set_id == vs_id)
                .where(VariableSetAssignment.workspace_id == workspace_id)
            )

    async def get_workspace_assignments(self, workspace_id: str) -> list[dict]:
        """Return variable sets attached to *workspace_id*, ordered by priority desc."""
        from backend.db.database import get_session
        from backend.db.models import VariableSet, VariableSetAssignment
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            rows = (await session.execute(
                sa_select(VariableSet)
                .join(VariableSetAssignment,
                      VariableSetAssignment.variable_set_id == VariableSet.id)
                .where(VariableSetAssignment.workspace_id == workspace_id)
                .order_by(VariableSetAssignment.priority.desc())
            )).scalars().all()
            h = _load_helpers()
            return [h.varset_to_dict(r, include_values=True) for r in rows]

    async def get_global_sets(self, org_id: str) -> list[dict]:
        """Return all global variable sets for *org_id*."""
        from backend.db.database import get_session
        from backend.db.models import VariableSet
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            rows = (await session.execute(
                sa_select(VariableSet)
                .where(VariableSet.org_id == org_id)
                .where(VariableSet.is_global.is_(True))
            )).scalars().all()
            h = _load_helpers()
            return [h.varset_to_dict(r, include_values=True) for r in rows]
