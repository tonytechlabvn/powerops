"""API key authentication middleware.

Validates the X-API-Key header against hashed keys stored in the User table.
Skipped for public paths: /api/health, /docs, /redoc, /openapi.json.
"""
from __future__ import annotations

import hashlib
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Paths that bypass authentication entirely
_PUBLIC_PATHS = frozenset([
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
])


def _hash_key(api_key: str) -> str:
    """Return SHA-256 hex digest of the raw API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce X-API-Key authentication on all non-public routes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Allow public paths and frontend routes through without auth
        if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PATHS):
            return await call_next(request)
        # Skip auth for non-API paths (frontend SPA, static assets)
        if not path.startswith("/api/"):
            return await call_next(request)

        # If no users exist in DB, skip auth entirely (MVP bootstrap mode)
        if await _no_users_exist():
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "").strip()
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header"},
            )

        user = await _lookup_user(api_key)
        if user is None:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"},
            )

        # Attach user name to request state for downstream use
        request.state.user = user
        return await call_next(request)


async def _lookup_user(api_key: str):
    """Return the User ORM object if the key is valid, else None."""
    try:
        from backend.db.database import get_session
        from backend.db.models import User
        from sqlalchemy import select as sa_select

        key_hash = _hash_key(api_key)
        async with get_session() as session:
            return (
                await session.execute(
                    sa_select(User).where(User.api_key_hash == key_hash)
                )
            ).scalar_one_or_none()
    except Exception as exc:
        logger.error("Auth lookup failed: %s", exc)
        return None


async def _no_users_exist() -> bool:
    """Return True if the User table is empty (bootstrap mode)."""
    try:
        from backend.db.database import get_session
        from backend.db.models import User
        from sqlalchemy import func, select as sa_select

        async with get_session() as session:
            count = (await session.execute(sa_select(func.count(User.id)))).scalar()
            return count == 0
    except Exception:
        return True  # If DB not ready, skip auth


def hash_api_key(api_key: str) -> str:
    """Public helper for hashing a key before storing it in the DB."""
    return _hash_key(api_key)
