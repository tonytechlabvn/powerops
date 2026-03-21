"""Team management endpoints (admin only).

GET    /api/teams                                  — list teams
POST   /api/teams                                  — create team
POST   /api/teams/{id}/members                     — add member
DELETE /api/teams/{id}/members/{user_id}           — remove member
PUT    /api/teams/{id}/permissions/{workspace_id}  — set permission level
DELETE /api/teams/{id}/permissions/{workspace_id}  — remove permission
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select as sa_select

from backend.db.database import get_session
from backend.db.models import Organization, Team, TeamMembership, User, WorkspacePermission, Workspace

logger = logging.getLogger(__name__)


def _load_schema(rel: str, alias: str):
    full = f"backend.api.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_schemas = _load_schema("schemas/auth-schemas.py", "schemas.auth_schemas")

router = APIRouter(prefix="/api/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str
    is_admin: bool = False


def _require_auth(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state if isinstance(state, dict) else {"user_id": getattr(state, "id", None)}


def _team_to_response(team: Team) -> _schemas.TeamResponse:
    return _schemas.TeamResponse(
        id=team.id,
        name=team.name,
        is_admin=team.is_admin,
        member_count=len(team.memberships),
    )


@router.get("", response_model=list[_schemas.TeamResponse])
async def list_teams(request: Request):
    """List all teams in the organisation."""
    _require_auth(request)
    async with get_session() as session:
        teams = (await session.execute(sa_select(Team).order_by(Team.created_at))).scalars().all()
        result = [_team_to_response(t) for t in teams]
    return result


@router.post("", response_model=_schemas.TeamResponse, status_code=201)
async def create_team(body: CreateTeamRequest, request: Request):
    """Create a new team."""
    _require_auth(request)
    async with get_session() as session:
        org = (await session.execute(sa_select(Organization))).scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=500, detail="No organisation found")

        # Check for duplicate name within org
        existing = (await session.execute(
            sa_select(Team).where(Team.org_id == org.id, Team.name == body.name)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Team name already exists")

        team = Team(name=body.name, org_id=org.id, is_admin=body.is_admin)
        session.add(team)
        await session.flush()
        result = _team_to_response(team)

    logger.info("Created team %s", body.name)
    return result


@router.post("/{team_id}/members", status_code=201)
async def add_member(team_id: str, body: _schemas.TeamMemberRequest, request: Request):
    """Add a user to a team."""
    _require_auth(request)
    async with get_session() as session:
        team = (await session.execute(
            sa_select(Team).where(Team.id == team_id)
        )).scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")

        user = (await session.execute(
            sa_select(User).where(User.id == body.user_id)
        )).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        already = (await session.execute(
            sa_select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == body.user_id,
            )
        )).scalar_one_or_none()
        if already:
            raise HTTPException(status_code=409, detail="User already a member")

        session.add(TeamMembership(team_id=team_id, user_id=body.user_id))

    logger.info("Added user %s to team %s", body.user_id, team_id)
    return {"detail": "Member added"}


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_member(team_id: str, user_id: str, request: Request):
    """Remove a user from a team."""
    _require_auth(request)
    async with get_session() as session:
        membership = (await session.execute(
            sa_select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
            )
        )).scalar_one_or_none()
        if membership is None:
            raise HTTPException(status_code=404, detail="Membership not found")
        await session.delete(membership)

    logger.info("Removed user %s from team %s", user_id, team_id)


@router.put("/{team_id}/permissions/{workspace_id}", status_code=200)
async def set_permission(
    team_id: str,
    workspace_id: str,
    body: _schemas.PermissionRequest,
    request: Request,
):
    """Set or update a team's permission level on a workspace."""
    _require_auth(request)
    async with get_session() as session:
        team = (await session.execute(
            sa_select(Team).where(Team.id == team_id)
        )).scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")

        workspace = (await session.execute(
            sa_select(Workspace).where(Workspace.id == workspace_id)
        )).scalar_one_or_none()
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        perm = (await session.execute(
            sa_select(WorkspacePermission).where(
                WorkspacePermission.team_id == team_id,
                WorkspacePermission.workspace_id == workspace_id,
            )
        )).scalar_one_or_none()

        if perm:
            perm.level = body.level
            session.add(perm)
        else:
            session.add(WorkspacePermission(
                team_id=team_id,
                workspace_id=workspace_id,
                level=body.level,
            ))

    logger.info("Set team %s permission on workspace %s to %s", team_id, workspace_id, body.level)
    return {"detail": f"Permission set to {body.level}"}


@router.delete("/{team_id}/permissions/{workspace_id}", status_code=204)
async def remove_permission(team_id: str, workspace_id: str, request: Request):
    """Remove a team's permission on a workspace."""
    _require_auth(request)
    async with get_session() as session:
        perm = (await session.execute(
            sa_select(WorkspacePermission).where(
                WorkspacePermission.team_id == team_id,
                WorkspacePermission.workspace_id == workspace_id,
            )
        )).scalar_one_or_none()
        if perm is None:
            raise HTTPException(status_code=404, detail="Permission not found")
        await session.delete(perm)

    logger.info("Removed team %s permission on workspace %s", team_id, workspace_id)
