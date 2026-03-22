"""Variable set manager — CRUD and variable management for variable sets.

Assignment ops → variable-set-assignment-manager.py
Encryption/serialization helpers → variable-set-encryption-helpers.py
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
import uuid
from pathlib import Path as _Path

logger = logging.getLogger(__name__)

_MAX_SETS_PER_ORG = 50
_MAX_VARS_PER_SET = 200


def _helpers():
    alias = "backend.core.variable_set_encryption_helpers"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(
        alias, _Path(__file__).parent / "variable-set-encryption-helpers.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _new_id() -> str:
    return str(uuid.uuid4())


class VariableSetManager:
    """Async service: variable set CRUD + variable management.

    For workspace assignment use VariableSetAssignmentManager.
    """

    # ------------------------------------------------------------------
    # Variable set CRUD
    # ------------------------------------------------------------------

    async def create(self, org_id: str, name: str, description: str = "",
                     is_global: bool = False) -> dict:
        from backend.db.database import get_session
        from backend.db.models import VariableSet
        from sqlalchemy import select as sa_select, func as sa_func

        async with get_session() as session:
            count = (await session.execute(
                sa_select(sa_func.count()).select_from(VariableSet)
                .where(VariableSet.org_id == org_id)
            )).scalar_one()
            if count >= _MAX_SETS_PER_ORG:
                raise ValueError(f"Organisation reached the {_MAX_SETS_PER_ORG} variable-set limit.")
            row = VariableSet(id=_new_id(), org_id=org_id, name=name,
                              description=description, is_global=is_global)
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return _helpers().varset_to_dict(row)

    async def list_sets(self, org_id: str) -> list[dict]:
        from backend.db.database import get_session
        from backend.db.models import VariableSet
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            rows = (await session.execute(
                sa_select(VariableSet).where(VariableSet.org_id == org_id)
                .order_by(VariableSet.name)
            )).scalars().all()
            return [_helpers().varset_to_dict(r) for r in rows]

    async def get_set(self, vs_id: str) -> dict:
        from backend.db.database import get_session
        from backend.db.models import VariableSet
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            row = (await session.execute(
                sa_select(VariableSet).where(VariableSet.id == vs_id)
            )).scalar_one_or_none()
            if row is None:
                raise ValueError(f"Variable set not found: {vs_id}")
            return _helpers().varset_to_dict(row, include_values=True)

    async def update(self, vs_id: str, name: str | None = None,
                     description: str | None = None) -> dict:
        from backend.db.database import get_session
        from backend.db.models import VariableSet
        from sqlalchemy import select as sa_select

        async with get_session() as session:
            row = (await session.execute(
                sa_select(VariableSet).where(VariableSet.id == vs_id)
            )).scalar_one_or_none()
            if row is None:
                raise ValueError(f"Variable set not found: {vs_id}")
            if name is not None:
                row.name = name
            if description is not None:
                row.description = description
            session.add(row)
            return _helpers().varset_to_dict(row)

    async def delete(self, vs_id: str) -> None:
        from backend.db.database import get_session
        from backend.db.models import VariableSet
        from sqlalchemy import delete as sa_delete

        async with get_session() as session:
            await session.execute(sa_delete(VariableSet).where(VariableSet.id == vs_id))

    # ------------------------------------------------------------------
    # Variable management within a set
    # ------------------------------------------------------------------

    async def set_variable(self, vs_id: str, key: str, value: str,
                           category: str = "terraform", is_sensitive: bool = False,
                           is_hcl: bool = False, description: str = "") -> dict:
        from backend.db.database import get_session
        from backend.db.models import VariableSet, VariableSetVariable
        from sqlalchemy import select as sa_select, func as sa_func
        h = _helpers()
        stored = h.encrypt_value(value) if is_sensitive else value
        async with get_session() as session:
            if not (await session.execute(
                sa_select(sa_func.count()).select_from(VariableSet).where(VariableSet.id == vs_id)
            )).scalar_one():
                raise ValueError(f"Variable set not found: {vs_id}")
            existing = (await session.execute(
                sa_select(VariableSetVariable)
                .where(VariableSetVariable.variable_set_id == vs_id)
                .where(VariableSetVariable.key == key)
            )).scalar_one_or_none()

            if existing:
                existing.value = stored
                existing.is_sensitive = is_sensitive
                existing.is_hcl = is_hcl
                existing.category = category
                existing.description = description
                session.add(existing)
                return h.var_to_dict(existing, include_value=True)

            count = (await session.execute(
                sa_select(sa_func.count()).select_from(VariableSetVariable)
                .where(VariableSetVariable.variable_set_id == vs_id)
            )).scalar_one()
            if count >= _MAX_VARS_PER_SET:
                raise ValueError(f"Variable set reached the {_MAX_VARS_PER_SET} variable limit.")

            var = VariableSetVariable(
                id=_new_id(), variable_set_id=vs_id, key=key,
                value=stored, is_sensitive=is_sensitive,
                is_hcl=is_hcl, category=category, description=description,
            )
            session.add(var)
            await session.flush()
            return h.var_to_dict(var, include_value=True)

    async def delete_variable(self, var_id: str) -> None:
        from backend.db.database import get_session
        from backend.db.models import VariableSetVariable
        from sqlalchemy import delete as sa_delete

        async with get_session() as session:
            await session.execute(
                sa_delete(VariableSetVariable).where(VariableSetVariable.id == var_id)
            )

    # Assignment delegation — load VariableSetAssignmentManager on demand
    def _assignment_mgr(self):
        alias = "backend.core.variable_set_assignment_manager"
        if alias in _sys.modules:
            return _sys.modules[alias].VariableSetAssignmentManager()
        spec = _ilu.spec_from_file_location(alias, _Path(__file__).parent / "variable-set-assignment-manager.py")
        mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
        _sys.modules[alias] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.VariableSetAssignmentManager()

    async def assign_to_workspace(self, vs_id: str, workspace_id: str, priority: int = 0) -> None:
        await self._assignment_mgr().assign_to_workspace(vs_id, workspace_id, priority)

    async def unassign_from_workspace(self, vs_id: str, workspace_id: str) -> None:
        await self._assignment_mgr().unassign_from_workspace(vs_id, workspace_id)

    async def get_workspace_assignments(self, workspace_id: str) -> list[dict]:
        return await self._assignment_mgr().get_workspace_assignments(workspace_id)

    async def get_global_sets(self, org_id: str) -> list[dict]:
        return await self._assignment_mgr().get_global_sets(org_id)
