"""Pydantic schemas for Phase 2: Auth & RBAC endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    org_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TeamSummary(BaseModel):
    id: str
    name: str
    is_admin: bool

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime
    teams: list[str] = []

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
