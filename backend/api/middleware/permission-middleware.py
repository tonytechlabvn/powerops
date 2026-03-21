"""Permission-checking FastAPI dependency factory.

Usage in route:
    from backend.api.middleware import permission_middleware as _pm
    ...
    async def my_route(
        workspace_id: str,
        _: None = Depends(_pm.require_permission("workspace_id", "write")),
    ): ...

Level hierarchy (highest → lowest): admin > write > plan > read
Admin-team members bypass all workspace-level checks.
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select as sa_select

from backend.db.database import get_session
from backend.db.models import Team, TeamMembership, WorkspacePermission, Workspace

logger = logging.getLogger(__name__)

# Ordered from lowest to highest privilege
_LEVEL_RANK: dict[str, int] = {
    "read":  1,
    "plan":  2,
    "write": 3,
    "admin": 4,
}


def require_permission(workspace_param: str, level: str) -> Callable:
    """Return a FastAPI dependency that enforces workspace permission.

    Args:
        workspace_param: Name of the path parameter holding the workspace id.
        level: Minimum required level ("read" | "plan" | "write" | "admin").
    """
    required_rank = _LEVEL_RANK.get(level, 0)

    async def _check(request: Request) -> None:
        # Resolve authenticated user
        state = getattr(request.state, "user", None)
        if state is None:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id: str | None = (
            state.get("user_id") if isinstance(state, dict)
            else getattr(state, "id", None)
        )
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Resolve workspace_id from path params
        workspace_id: str | None = request.path_params.get(workspace_param)
        if not workspace_id:
            raise HTTPException(
                status_code=400,
                detail=f"Missing path parameter '{workspace_param}'",
            )

        async with get_session() as session:
            # Verify workspace exists
            workspace = (await session.execute(
                sa_select(Workspace).where(Workspace.id == workspace_id)
            )).scalar_one_or_none()
            if workspace is None:
                raise HTTPException(status_code=404, detail="Workspace not found")

            # Collect user's team ids and check admin flag
            memberships = (await session.execute(
                sa_select(TeamMembership).where(TeamMembership.user_id == user_id)
            )).scalars().all()

            if not memberships:
                raise HTTPException(
                    status_code=403,
                    detail="No team membership — insufficient permissions",
                )

            team_ids = [m.team_id for m in memberships]

            # Load teams to check is_admin flag
            teams = (await session.execute(
                sa_select(Team).where(Team.id.in_(team_ids))
            )).scalars().all()

            # Admin-team members bypass all checks
            if any(t.is_admin for t in teams):
                return

            # Find highest permission level across all user teams for this workspace
            perms = (await session.execute(
                sa_select(WorkspacePermission).where(
                    WorkspacePermission.team_id.in_(team_ids),
                    WorkspacePermission.workspace_id == workspace_id,
                )
            )).scalars().all()

            if not perms:
                raise HTTPException(
                    status_code=403,
                    detail=f"No permission on workspace '{workspace_id}'",
                )

            best_rank = max(_LEVEL_RANK.get(p.level, 0) for p in perms)
            if best_rank < required_rank:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Requires '{level}' permission on this workspace "
                        f"(current: {_rank_to_level(best_rank)})"
                    ),
                )

    return Depends(_check)


def _rank_to_level(rank: int) -> str:
    for lvl, r in _LEVEL_RANK.items():
        if r == rank:
            return lvl
    return "none"
