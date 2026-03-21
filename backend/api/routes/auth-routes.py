"""Auth endpoints: register, login, refresh, logout, me.

POST /api/auth/register  — create user + org (first user = admin)
POST /api/auth/login     — email/password → access token + refresh cookie
POST /api/auth/refresh   — rotate access token via refresh cookie
POST /api/auth/logout    — clear refresh cookie
GET  /api/auth/me        — current user profile
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func, select as sa_select

from backend.db.database import get_session
from backend.db.models import Organization, Team, TeamMembership, User

logger = logging.getLogger(__name__)

# Load kebab-case modules
def _load_core(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent.parent / "core" / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

def _load_schema(rel: str, alias: str):
    full = f"backend.api.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

_auth_svc = _load_core("auth-service.py", "auth_service")
_schemas  = _load_schema("schemas/auth-schemas.py", "schemas.auth_schemas")

router = APIRouter(prefix="/api/auth", tags=["auth"])

_REFRESH_COOKIE = "tb_refresh"


@router.post("/register", response_model=_schemas.TokenResponse)
async def register(body: _schemas.RegisterRequest, response: Response):
    """Register a new user. First-ever user auto-creates an org and becomes admin."""
    async with get_session() as session:
        # Reject duplicate email
        existing = (await session.execute(
            sa_select(User).where(User.email == body.email)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        # Determine if this is the very first user
        user_count = (await session.execute(sa_select(func.count(User.id)))).scalar() or 0
        is_first = user_count == 0

        # Create or reuse org
        if is_first:
            org_name = body.org_name or f"{body.name}'s Org"
            org = Organization(name=org_name)
            session.add(org)
            await session.flush()  # populate org.id
        else:
            # Subsequent users join first org (single-org mode)
            org = (await session.execute(sa_select(Organization))).scalar_one_or_none()
            if org is None:
                raise HTTPException(status_code=500, detail="No organisation found")

        # Create user
        user = User(
            email=body.email,
            password_hash=_auth_svc.hash_password(body.password),
            name=body.name,
            org_id=org.id,
        )
        session.add(user)
        await session.flush()

        if is_first:
            # Bootstrap admin team
            admin_team = Team(name="Admins", org_id=org.id, is_admin=True)
            session.add(admin_team)
            await session.flush()
            session.add(TeamMembership(team_id=admin_team.id, user_id=user.id))

        user_id, org_id = user.id, org.id

    access = _auth_svc.create_access_token(user_id, org_id)
    refresh = _auth_svc.create_refresh_token(user_id)
    from backend.core.config import get_settings
    s = get_settings()
    _set_refresh_cookie(response, refresh, s.jwt_refresh_ttl_days * 86400)
    logger.info("Registered user %s (first=%s)", body.email, is_first)
    return _schemas.TokenResponse(access_token=access)


@router.post("/login", response_model=_schemas.TokenResponse)
async def login(body: _schemas.LoginRequest, response: Response):
    """Authenticate with email/password. Returns access token; sets refresh cookie."""
    async with get_session() as session:
        user = (await session.execute(
            sa_select(User).where(User.email == body.email, User.is_active == True)
        )).scalar_one_or_none()

    if user is None or not _auth_svc.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access = _auth_svc.create_access_token(user.id, user.org_id or "")
    refresh = _auth_svc.create_refresh_token(user.id)
    from backend.core.config import get_settings
    s = get_settings()
    _set_refresh_cookie(response, refresh, s.jwt_refresh_ttl_days * 86400)
    logger.info("User %s logged in", body.email)
    return _schemas.TokenResponse(access_token=access)


@router.post("/refresh", response_model=_schemas.TokenResponse)
async def refresh_token(request: Request, response: Response):
    """Exchange a valid refresh cookie for a new access token."""
    raw = request.cookies.get(_REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        claims = _auth_svc.verify_token(raw)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = claims["sub"]
    async with get_session() as session:
        user = (await session.execute(
            sa_select(User).where(User.id == user_id, User.is_active == True)
        )).scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access = _auth_svc.create_access_token(user.id, user.org_id or "")
    return _schemas.TokenResponse(access_token=access)


@router.post("/logout")
async def logout(response: Response):
    """Clear the refresh token cookie."""
    response.delete_cookie(_REFRESH_COOKIE, path="/", httponly=True, samesite="lax")
    return {"detail": "Logged out"}


@router.get("/me", response_model=_schemas.UserResponse)
async def me(request: Request):
    """Return current user's profile and team names."""
    state = getattr(request.state, "user", None)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = state.get("user_id") if isinstance(state, dict) else getattr(state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with get_session() as session:
        user = (await session.execute(
            sa_select(User).where(User.id == user_id)
        )).scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

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
# Helpers
# ---------------------------------------------------------------------------

def _set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=False,  # set True behind HTTPS proxy
        path="/",
    )
