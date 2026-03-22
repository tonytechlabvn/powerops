"""Auth endpoints: Keycloak OIDC config, callback, logout, me.

GET  /api/auth/keycloak-config — returns Keycloak OIDC params for frontend redirect
POST /api/auth/callback        — exchange auth code for tokens (backend code flow)
POST /api/auth/logout          — clear session
GET  /api/auth/me              — current user profile
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select as sa_select
from sqlalchemy.orm import selectinload

from backend.db.database import get_session
from backend.db.models import TeamMembership, User

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


_schemas = _load_schema("schemas/auth-schemas.py", "schemas.auth_schemas")

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/keycloak-config")
async def keycloak_config():
    """Return Keycloak OIDC connection params for frontend to initiate login."""
    from backend.core.config import get_settings
    s = get_settings()
    # Use public URL for browser redirects, fallback to internal URL
    public_url = s.keycloak_public_url or s.keycloak_url
    return {
        "url": public_url,
        "realm": s.keycloak_realm,
        "clientId": "powerops-frontend",
    }


@router.post("/callback", response_model=_schemas.TokenResponse)
async def keycloak_callback(request: Request):
    """Exchange Keycloak authorization code for tokens (backend code flow).

    Frontend sends { code, redirect_uri } after Keycloak redirect.
    Backend exchanges code at Keycloak token endpoint, validates JWT,
    syncs user, and returns access_token.
    """
    from backend.core.config import get_settings
    s = get_settings()

    body = await request.json()
    code = body.get("code")
    redirect_uri = body.get("redirect_uri")
    code_verifier = body.get("code_verifier")
    if not code or not redirect_uri:
        raise HTTPException(status_code=400, detail="Missing code or redirect_uri")

    # Exchange auth code for tokens at Keycloak
    token_url = f"{s.keycloak_url}/realms/{s.keycloak_realm}/protocol/openid-connect/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": s.keycloak_client_id,
    }
    # PKCE: include code_verifier for proof of possession
    if code_verifier:
        token_data["code_verifier"] = code_verifier
    if s.keycloak_client_secret:
        token_data["client_secret"] = s.keycloak_client_secret

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=token_data)

    if resp.status_code != 200:
        logger.error("Keycloak token exchange failed: %s", resp.text)
        raise HTTPException(status_code=401, detail="Token exchange failed")

    tokens = resp.json()
    access_token = tokens.get("access_token")

    # Validate the token and sync user
    _kc_svc = _load_core("keycloak-auth-service.py", "keycloak_auth_service")
    try:
        claims = _kc_svc.validate_keycloak_jwt(access_token)
        await _kc_svc.sync_keycloak_user(claims)
    except Exception as exc:
        logger.error("Token validation after exchange failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token from Keycloak")

    return _schemas.TokenResponse(
        access_token=access_token,
        refresh_token=tokens.get("refresh_token", ""),
    )


@router.post("/refresh", response_model=_schemas.TokenResponse)
async def refresh_token(request: Request):
    """Exchange a Keycloak refresh token for a new access token."""
    from backend.core.config import get_settings
    s = get_settings()

    body = await request.json()
    refresh = body.get("refresh_token")
    if not refresh:
        raise HTTPException(status_code=400, detail="Missing refresh_token")

    token_url = f"{s.keycloak_url}/realms/{s.keycloak_realm}/protocol/openid-connect/token"
    token_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": s.keycloak_client_id,
    }
    if s.keycloak_client_secret:
        token_data["client_secret"] = s.keycloak_client_secret

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=token_data)

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")

    tokens = resp.json()
    return _schemas.TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token", refresh),
    )


@router.post("/logout")
async def logout(request: Request):
    """End Keycloak session (optional: revoke refresh token)."""
    from backend.core.config import get_settings
    s = get_settings()

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    refresh = body.get("refresh_token")

    if refresh:
        # Revoke at Keycloak
        logout_url = f"{s.keycloak_url}/realms/{s.keycloak_realm}/protocol/openid-connect/logout"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(logout_url, data={
                    "client_id": s.keycloak_client_id,
                    "refresh_token": refresh,
                })
        except Exception as exc:
            logger.warning("Keycloak logout revocation failed: %s", exc)

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
            sa_select(User)
            .where(User.id == user_id)
            .options(selectinload(User.team_memberships).selectinload(TeamMembership.team))
        )).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        team_names = [m.team.name for m in user.team_memberships if m.team]
        roles = state.get("roles", []) if isinstance(state, dict) else []
        return _schemas.UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
            teams=team_names,
            roles=roles,
        )
