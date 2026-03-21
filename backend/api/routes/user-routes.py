"""User management endpoints (admin only).

GET    /api/users       — list all users
POST   /api/users       — create user
PATCH  /api/users/{id}  — update user fields
DELETE /api/users/{id}  — deactivate user (soft delete)
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select as sa_select
from sqlalchemy.orm import selectinload

from backend.db.database import get_session
from backend.db.models import TeamMembership, User

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


def _load_core(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent.parent / "core" / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_schemas  = _load_schema("schemas/auth-schemas.py", "schemas.auth_schemas")
_auth_svc = _load_core("auth-service.py", "auth_service")

router = APIRouter(prefix="/api/users", tags=["users"])


# ---------------------------------------------------------------------------
# Request bodies (inline — simple enough to avoid extra file)
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_admin(request: Request) -> dict:
    """Extract user state and enforce admin-team membership."""
    state = getattr(request.state, "user", None)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if isinstance(state, dict):
        return state
    # ORM User object attached by old auth path — convert
    return {"user_id": getattr(state, "id", None), "is_admin": False}


def _user_to_response(user: User) -> _schemas.UserResponse:
    team_names = [m.team.name for m in user.team_memberships if m.team]
    return _schemas.UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        created_at=user.created_at,
        teams=team_names,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[_schemas.UserResponse])
async def list_users(request: Request):
    """List all users in the organisation."""
    _require_admin(request)
    async with get_session() as session:
        users = (await session.execute(
            sa_select(User)
            .options(selectinload(User.team_memberships).selectinload(TeamMembership.team))
            .order_by(User.created_at)
        )).scalars().all()
        result = [_user_to_response(u) for u in users]
    return result


@router.post("", response_model=_schemas.UserResponse, status_code=201)
async def create_user(body: CreateUserRequest, request: Request):
    """Create a new user (admin only)."""
    _require_admin(request)
    async with get_session() as session:
        existing = (await session.execute(
            sa_select(User).where(User.email == body.email)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        # Assign to first org found
        from backend.db.models import Organization
        org = (await session.execute(sa_select(Organization))).scalar_one_or_none()
        org_id = org.id if org else None

        user = User(
            email=body.email,
            password_hash=_auth_svc.hash_password(body.password),
            name=body.name,
            org_id=org_id,
        )
        session.add(user)
        await session.flush()
        result = _user_to_response(user)

    logger.info("Admin created user %s", body.email)
    return result


@router.patch("/{user_id}", response_model=_schemas.UserResponse)
async def update_user(user_id: str, body: UpdateUserRequest, request: Request):
    """Update user name or active status."""
    _require_admin(request)
    async with get_session() as session:
        user = (await session.execute(
            sa_select(User).where(User.id == user_id)
            .options(selectinload(User.team_memberships).selectinload(TeamMembership.team))
        )).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if body.name is not None:
            user.name = body.name
        if body.is_active is not None:
            user.is_active = body.is_active

        session.add(user)
        result = _user_to_response(user)

    return result


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(user_id: str, request: Request):
    """Deactivate (soft-delete) a user."""
    _require_admin(request)
    async with get_session() as session:
        user = (await session.execute(
            sa_select(User).where(User.id == user_id)
        )).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = False
        session.add(user)

    logger.info("User %s deactivated", user_id)
