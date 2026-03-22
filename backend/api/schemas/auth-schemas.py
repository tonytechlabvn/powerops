"""Pydantic schemas for Auth endpoints (Keycloak OIDC)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class TokenResponse(BaseModel):
    """Returned after Keycloak code exchange or token refresh."""
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"


class KeycloakConfigResponse(BaseModel):
    """Keycloak OIDC connection params for frontend redirect."""
    url: str
    realm: str
    clientId: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime
    teams: list[str] = []
    roles: list[str] = []

    model_config = {"from_attributes": True}


class TeamSummary(BaseModel):
    id: str
    name: str
    is_admin: bool

    model_config = {"from_attributes": True}


class TeamResponse(BaseModel):
    id: str
    name: str
    is_admin: bool
    member_count: int = 0

    model_config = {"from_attributes": True}


class TeamMemberRequest(BaseModel):
    user_id: str


class PermissionRequest(BaseModel):
    level: str

    @field_validator("level")
    @classmethod
    def valid_level(cls, v: str) -> str:
        allowed = {"read", "plan", "write", "admin"}
        if v not in allowed:
            raise ValueError(f"level must be one of {allowed}")
        return v


class APITokenCreateRequest(BaseModel):
    name: str


class APITokenResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APITokenCreatedResponse(BaseModel):
    """Returned once on token creation — includes raw token."""
    id: str
    name: str
    token: str
