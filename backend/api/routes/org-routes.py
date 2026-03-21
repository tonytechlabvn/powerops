"""Organisation and API token management endpoints.

GET    /api/org             — org info
GET    /api/org/tokens      — list current user's API tokens
POST   /api/org/tokens      — create API token (raw token shown once)
DELETE /api/org/tokens/{id} — revoke token
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from datetime import datetime, timezone
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select as sa_select

from backend.db.database import get_session
from backend.db.models import APIToken, Organization

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

router = APIRouter(prefix="/api/org", tags=["organization"])


def _require_auth(request: Request) -> str:
    """Return user_id from request state or raise 401."""
    state = getattr(request.state, "user", None)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if isinstance(state, dict):
        user_id = state.get("user_id")
    else:
        user_id = getattr(state, "id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


@router.get("", response_model=dict)
async def get_org(request: Request):
    """Return current organisation info."""
    _require_auth(request)
    async with get_session() as session:
        org = (await session.execute(sa_select(Organization))).scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail="No organisation found")
        result = {"id": org.id, "name": org.name, "created_at": org.created_at}
    return result


@router.get("/tokens", response_model=list[_schemas.APITokenResponse])
async def list_tokens(request: Request):
    """List current user's non-revoked API tokens."""
    user_id = _require_auth(request)
    async with get_session() as session:
        tokens = (await session.execute(
            sa_select(APIToken)
            .where(APIToken.user_id == user_id)
            .order_by(APIToken.created_at.desc())
        )).scalars().all()
        result = [
            _schemas.APITokenResponse(
                id=t.id,
                name=t.name,
                created_at=t.created_at,
                last_used_at=t.last_used_at,
                revoked_at=t.revoked_at,
            )
            for t in tokens
        ]
    return result


@router.post("/tokens", response_model=_schemas.APITokenCreatedResponse, status_code=201)
async def create_token(body: _schemas.APITokenCreateRequest, request: Request):
    """Create a new API token. Raw token is returned once — store it securely."""
    user_id = _require_auth(request)
    raw_token, token_hash = _auth_svc.create_api_token(user_id, body.name)

    async with get_session() as session:
        token_obj = APIToken(
            user_id=user_id,
            name=body.name,
            token_hash=token_hash,
        )
        session.add(token_obj)
        await session.flush()
        token_id = token_obj.id

    logger.info("Created API token '%s' for user %s", body.name, user_id)
    return _schemas.APITokenCreatedResponse(id=token_id, name=body.name, token=raw_token)


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_token(token_id: str, request: Request):
    """Revoke (soft-delete) an API token."""
    user_id = _require_auth(request)
    async with get_session() as session:
        token_obj = (await session.execute(
            sa_select(APIToken).where(
                APIToken.id == token_id,
                APIToken.user_id == user_id,
            )
        )).scalar_one_or_none()
        if token_obj is None:
            raise HTTPException(status_code=404, detail="Token not found")
        if token_obj.revoked_at is not None:
            raise HTTPException(status_code=409, detail="Token already revoked")
        token_obj.revoked_at = datetime.now(timezone.utc)
        session.add(token_obj)

    logger.info("Revoked API token %s for user %s", token_id, user_id)
