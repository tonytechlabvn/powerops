"""Dual-mode authentication middleware: Keycloak JWT (RS256) + X-API-Key.

Resolution order:
  1. Authorization: Bearer <jwt>  → validate via Keycloak JWKS, sync user
  2. X-API-Key: tb_xxxxx          → hash+lookup, set request.state.user dict
  3. Public paths                 → pass through without auth
  4. Non-API paths (SPA/static)   → pass through without auth
  5. Otherwise                    → 401
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Exact paths that bypass auth
_PUBLIC_EXACT: frozenset[str] = frozenset([
    "/api/health",
    "/api/auth/keycloak-config",
    "/api/auth/callback",
    "/api/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
])

# Prefix-based public paths
_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/webhooks/",
    "/auth/",
    "/docs/",
    "/redoc/",
)


def _load_core(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent.parent / "core" / rel
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    """Attach request.state.user for authenticated requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Non-API paths (SPA, static assets) — skip
        if not path.startswith("/api/"):
            return await call_next(request)

        # Explicitly public API paths — skip
        if _is_public(path):
            return await call_next(request)

        # --- Try Keycloak JWT Bearer ---
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            user_state = await _decode_keycloak_jwt(token)
            if user_state is None:
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
            request.state.user = user_state
            return await call_next(request)

        # --- Try API key ---
        api_key = request.headers.get("X-API-Key", "").strip()
        if api_key:
            user_id = await _verify_api_key(api_key)
            if user_id is None:
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
            request.state.user = {"user_id": user_id, "org_id": None, "via": "api_key"}
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required (Bearer token or X-API-Key)"},
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _decode_keycloak_jwt(token: str) -> dict | None:
    """Validate Keycloak JWT via JWKS and sync user to DB."""
    try:
        _kc_svc = _load_core("keycloak-auth-service.py", "keycloak_auth_service")
        claims = _kc_svc.validate_keycloak_jwt(token)
        # Auto-provision/sync user in DB
        user_state = await _kc_svc.sync_keycloak_user(claims)
        return user_state
    except Exception as exc:
        logger.debug("Keycloak JWT validation failed: %s", exc)
        return None


async def _verify_api_key(raw_token: str) -> str | None:
    """Hash and look up API key; return user_id or None."""
    try:
        _auth_svc = _load_core("auth-service.py", "auth_service")
        return await _auth_svc.verify_api_token(raw_token)
    except Exception as exc:
        logger.error("API key verification error: %s", exc)
        return None
