"""Auth service: API token management.

Password auth removed — Keycloak handles all user authentication.
This module retains API token (X-API-Key) CRUD for CLI/automation access.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API token helpers
# ---------------------------------------------------------------------------


def _hash_raw_token(raw_token: str) -> str:
    """SHA-256 hex digest of a raw API token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_api_token(user_id: str, name: str) -> tuple[str, str]:
    """Generate a new API token. Returns (raw_token, token_hash).

    raw_token is shown to the user ONCE; only token_hash is persisted.
    """
    raw = "tb_" + secrets.token_hex(32)
    return raw, _hash_raw_token(raw)


async def verify_api_token(raw_token: str) -> Optional[str]:
    """Look up raw token in DB; update last_used_at; return user_id or None."""
    try:
        from backend.db.database import get_session
        from backend.db.models import APIToken
        from sqlalchemy import select as sa_select

        token_hash = _hash_raw_token(raw_token)
        async with get_session() as session:
            result = await session.execute(
                sa_select(APIToken).where(
                    APIToken.token_hash == token_hash,
                    APIToken.revoked_at.is_(None),
                )
            )
            token_obj: Optional[APIToken] = result.scalar_one_or_none()
            if token_obj is None:
                return None
            token_obj.last_used_at = datetime.now(timezone.utc)
            session.add(token_obj)
            return token_obj.user_id
    except Exception as exc:
        logger.error("API token verification failed: %s", exc)
        return None
