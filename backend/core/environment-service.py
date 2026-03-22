"""Environment service — CRUD, variable management, and workspace linking (Phase 2).

Provides:
  EnvironmentService.create_environment        — create a named env in an org
  EnvironmentService.list_environments         — list envs for an org
  EnvironmentService.get_environment           — get single env by ID
  EnvironmentService.update_environment        — patch env fields
  EnvironmentService.delete_environment        — delete (guards protected)
  EnvironmentService.set_variable              — upsert an env-level variable
  EnvironmentService.delete_variable           — remove env-level variable
  EnvironmentService.get_variables             — list env variables (sensitive masked)
  EnvironmentService.link_workspace            — assign workspace to environment
  EnvironmentService.get_environment_workspaces — list workspaces in environment
  EnvironmentService.get_effective_variables   — merged env+workspace vars
  EnvironmentService.build_env_dict            — flat dict for terraform CLI
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_SENSITIVE_MASK = "***"


def _mask(value: str, is_sensitive: bool) -> str:
    return _SENSITIVE_MASK if is_sensitive else value


def _row_to_var_dict(row: Any, reveal: bool = False) -> dict:
    return {
        "id": row.id,
        "key": row.key,
        "value": row.value if reveal else _mask(row.value, row.is_sensitive),
        "is_sensitive": row.is_sensitive,
        "is_hcl": row.is_hcl,
        "category": row.category,
        "description": row.description,
    }


class EnvironmentService:
    """Business logic for Environment and variable management."""

    # ------------------------------------------------------------------
    # Environment CRUD
    # ------------------------------------------------------------------

    async def create_environment(
        self,
        session: AsyncSession,
        org_id: str,
        name: str,
        description: str = "",
        color: str = "#6366f1",
        is_protected: bool = False,
        auto_apply: bool = False,
    ) -> dict:
        from backend.db.models import Environment
        env = Environment(
            org_id=org_id,
            name=name,
            description=description,
            color=color,
            is_protected=is_protected,
            auto_apply=auto_apply,
        )
        session.add(env)
        await session.flush()
        await session.refresh(env)
        return self._env_to_dict(env, var_count=0, ws_count=0)

    async def list_environments(self, session: AsyncSession, org_id: str) -> list[dict]:
        from backend.db.models import Environment, Workspace
        stmt = select(Environment).where(Environment.org_id == org_id).order_by(Environment.name)
        rows = (await session.execute(stmt)).scalars().all()
        result = []
        for env in rows:
            ws_count = (
                await session.execute(
                    select(func.count()).select_from(Workspace).where(Workspace.environment_id == env.id)
                )
            ).scalar_one()
            result.append(self._env_to_dict(env, var_count=len(env.variables), ws_count=ws_count))
        return result

    async def get_environment(self, session: AsyncSession, env_id: str) -> dict:
        from backend.db.models import Environment, Workspace
        env = await session.get(Environment, env_id)
        if not env:
            raise KeyError(f"Environment {env_id} not found")
        ws_count = (
            await session.execute(
                select(func.count()).select_from(Workspace).where(Workspace.environment_id == env_id)
            )
        ).scalar_one()
        return self._env_to_dict(env, var_count=len(env.variables), ws_count=ws_count)

    async def update_environment(self, session: AsyncSession, env_id: str, **kwargs: Any) -> dict:
        from backend.db.models import Environment
        env = await session.get(Environment, env_id)
        if not env:
            raise KeyError(f"Environment {env_id} not found")
        for field, value in kwargs.items():
            if value is not None and hasattr(env, field):
                setattr(env, field, value)
        await session.flush()
        return await self.get_environment(session, env_id)

    async def delete_environment(self, session: AsyncSession, env_id: str, force: bool = False) -> None:
        from backend.db.models import Environment
        env = await session.get(Environment, env_id)
        if not env:
            raise KeyError(f"Environment {env_id} not found")
        if env.is_protected and not force:
            raise PermissionError("Protected environments require force=true to delete")
        await session.delete(env)

    # ------------------------------------------------------------------
    # Variable management
    # ------------------------------------------------------------------

    async def set_variable(
        self,
        session: AsyncSession,
        env_id: str,
        key: str,
        value: str,
        is_sensitive: bool = False,
        is_hcl: bool = False,
        category: str = "terraform",
        description: str = "",
    ) -> dict:
        from backend.db.models import EnvironmentVariable
        stmt = select(EnvironmentVariable).where(
            EnvironmentVariable.environment_id == env_id,
            EnvironmentVariable.key == key,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.value = value
            existing.is_sensitive = is_sensitive
            existing.is_hcl = is_hcl
            existing.category = category
            existing.description = description
            var = existing
        else:
            var = EnvironmentVariable(
                environment_id=env_id, key=key, value=value,
                is_sensitive=is_sensitive, is_hcl=is_hcl,
                category=category, description=description,
            )
            session.add(var)
        await session.flush()
        return _row_to_var_dict(var)

    async def delete_variable(self, session: AsyncSession, env_id: str, key: str) -> None:
        from backend.db.models import EnvironmentVariable
        stmt = delete(EnvironmentVariable).where(
            EnvironmentVariable.environment_id == env_id,
            EnvironmentVariable.key == key,
        )
        await session.execute(stmt)

    async def get_variables(self, session: AsyncSession, env_id: str, reveal: bool = False) -> list[dict]:
        from backend.db.models import EnvironmentVariable
        stmt = select(EnvironmentVariable).where(
            EnvironmentVariable.environment_id == env_id
        ).order_by(EnvironmentVariable.key)
        rows = (await session.execute(stmt)).scalars().all()
        return [_row_to_var_dict(r, reveal) for r in rows]

    # ------------------------------------------------------------------
    # Workspace linking
    # ------------------------------------------------------------------

    async def link_workspace(self, session: AsyncSession, workspace_id: str, env_id: str) -> None:
        from backend.db.models import Workspace
        ws = await session.get(Workspace, workspace_id)
        if not ws:
            raise KeyError(f"Workspace {workspace_id} not found")
        ws.environment_id = env_id
        await session.flush()

    async def get_environment_workspaces(self, session: AsyncSession, env_id: str) -> list[dict]:
        from backend.db.models import Workspace
        stmt = select(Workspace).where(Workspace.environment_id == env_id).order_by(Workspace.name)
        rows = (await session.execute(stmt)).scalars().all()
        return [{"id": w.id, "name": w.name, "provider": w.provider} for w in rows]

    # ------------------------------------------------------------------
    # Variable inheritance
    # ------------------------------------------------------------------

    async def get_effective_variables(
        self, session: AsyncSession, workspace_id: str, reveal: bool = False
    ) -> list[dict]:
        from backend.db.models import Workspace, WorkspaceVariable
        ws = await session.get(Workspace, workspace_id)
        env_vars: dict[str, dict] = {}
        if ws and ws.environment_id:
            for v in await self.get_variables(session, ws.environment_id, reveal):
                env_vars[v["key"]] = {**v, "source": "environment"}
        ws_stmt = select(WorkspaceVariable).where(WorkspaceVariable.workspace_id == workspace_id)
        ws_rows = (await session.execute(ws_stmt)).scalars().all()
        for row in ws_rows:
            env_vars[row.key] = {**_row_to_var_dict(row, reveal), "source": "workspace"}
        return sorted(env_vars.values(), key=lambda x: x["key"])

    async def build_env_dict(self, session: AsyncSession, workspace_id: str) -> dict[str, str]:
        """Return flat dict of env vars for the terraform subprocess."""
        effective = await self.get_effective_variables(session, workspace_id, reveal=True)
        result: dict[str, str] = {}
        for v in effective:
            if v["category"] == "terraform":
                result[f"TF_VAR_{v['key']}"] = v["value"]
            else:
                result[v["key"]] = v["value"]
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _env_to_dict(self, env: Any, var_count: int, ws_count: int) -> dict:
        return {
            "id": env.id,
            "name": env.name,
            "description": env.description,
            "org_id": env.org_id,
            "color": env.color,
            "is_protected": env.is_protected,
            "auto_apply": env.auto_apply,
            "created_at": env.created_at,
            "variable_count": var_count,
            "workspace_count": ws_count,
        }
