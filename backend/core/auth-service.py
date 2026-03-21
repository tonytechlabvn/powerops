"""Auth service: password hashing, JWT lifecycle, and API token management.

Centralises all cryptographic operations so routes stay thin.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt

logger = logging.getLogger(__name__)


def _settings():
    from backend.core.config import get_settings
    return get_settings()


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return bcrypt hash of password using configured rounds."""
    rounds = _settings().bcrypt_rounds
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Return True if password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, org_id: str) -> str:
    """Issue a short-lived JWT access token."""
    s = _settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org": org_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_access_ttl_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """Issue a long-lived JWT refresh token (no org claim)."""
    s = _settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=s.jwt_refresh_ttl_days),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict:
    """Decode and return JWT claims. Raises jwt.PyJWTError on invalid/expired."""
    s = _settings()
    return jwt.decode(token, s.jwt_secret, algorithms=["HS256"])


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
