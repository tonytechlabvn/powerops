"""Keycloak OIDC auth service: JWKS validation and user sync.

Validates Keycloak-issued JWTs via RS256 JWKS, extracts roles/groups,
and auto-provisions users in PowerOps DB on first login.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

# JWKS client cache — initialized lazily per realm URL
_jwks_client: Optional[PyJWKClient] = None
_jwks_client_url: str = ""
_JWKS_CACHE_TTL = 60  # seconds


def _settings():
    from backend.core.config import get_settings
    return get_settings()


def _get_jwks_client() -> PyJWKClient:
    """Return cached PyJWKClient, refreshing if Keycloak URL changed."""
    global _jwks_client, _jwks_client_url
    s = _settings()
    jwks_url = f"{s.keycloak_url}/realms/{s.keycloak_realm}/protocol/openid-connect/certs"
    if _jwks_client is None or _jwks_client_url != jwks_url:
        _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=_JWKS_CACHE_TTL)
        _jwks_client_url = jwks_url
    return _jwks_client


def validate_keycloak_jwt(token: str) -> dict:
    """Validate a Keycloak-issued JWT and return decoded claims.

    Verifies RS256 signature via JWKS, checks issuer and audience.
    Raises jwt.PyJWTError on invalid/expired tokens.
    """
    s = _settings()
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)

    # Accept tokens issued by both internal and public Keycloak URLs
    internal_issuer = f"{s.keycloak_url}/realms/{s.keycloak_realm}"
    public_url = s.keycloak_public_url or s.keycloak_url
    public_issuer = f"{public_url}/realms/{s.keycloak_realm}"

    # First try with public issuer (production), fallback to internal (docker)
    for issuer in {public_issuer, internal_issuer}:
        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=["powerops-api", "powerops-frontend", "account"],
                issuer=issuer,
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
            )
            return claims
        except jwt.InvalidIssuerError:
            continue

    # Neither issuer matched — raise with details
    raise jwt.InvalidIssuerError("Token issuer does not match configured Keycloak URLs")


def extract_roles(claims: dict) -> list[str]:
    """Extract realm roles from Keycloak JWT claims."""
    realm_access = claims.get("realm_access", {})
    return realm_access.get("roles", [])


def extract_groups(claims: dict) -> list[str]:
    """Extract group memberships from Keycloak JWT claims."""
    return claims.get("groups", [])


async def sync_keycloak_user(claims: dict) -> dict:
    """Create or update PowerOps User from Keycloak JWT claims.

    Auto-provisions user on first login. Returns dict with user_id, org_id,
    roles, and groups for request.state.user.
    """
    from backend.db.database import get_session
    from backend.db.models import User, Organization
    from sqlalchemy import select as sa_select, func
    from datetime import datetime, timezone

    keycloak_id = claims["sub"]
    email = claims.get("email", "")
    name = claims.get("preferred_username", claims.get("name", email))
    roles = extract_roles(claims)
    groups = extract_groups(claims)

    async with get_session() as session:
        # Look up by keycloak_id
        user = (await session.execute(
            sa_select(User).where(User.keycloak_id == keycloak_id)
        )).scalar_one_or_none()

        if user is None:
            # Auto-provision: first check if any org exists
            org = (await session.execute(sa_select(Organization))).scalar_one_or_none()
            if org is None:
                # Create default org for first Keycloak user
                org = Organization(name="Default Organization")
                session.add(org)
                await session.flush()

            user = User(
                keycloak_id=keycloak_id,
                email=email,
                name=name,
                org_id=org.id,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            logger.info("Auto-provisioned user %s (keycloak_id=%s)", email, keycloak_id)
        else:
            # Sync fields from Keycloak on each login
            user.email = email
            user.name = name
            user.last_login_at = datetime.now(timezone.utc)
            session.add(user)

        return {
            "user_id": user.id,
            "org_id": user.org_id,
            "keycloak_id": keycloak_id,
            "roles": roles,
            "groups": groups,
            "via": "keycloak",
        }
