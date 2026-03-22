"""Pydantic schemas for the Variable Sets API.

Used by variable-set-routes.py for request validation and response serialization.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Variable set CRUD
# ---------------------------------------------------------------------------


class CreateVariableSetRequest(BaseModel):
    name: str
    description: str = ""
    is_global: bool = False


class UpdateVariableSetRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class VariableSetVariable(BaseModel):
    """Single variable within a set (response shape)."""
    id: str
    variable_set_id: str
    key: str
    value: str          # empty string when is_sensitive=True and not revealed
    is_sensitive: bool
    is_hcl: bool
    category: str       # "terraform" | "env"
    description: str = ""


class VariableSetResponse(BaseModel):
    id: str
    name: str
    description: str
    org_id: str
    is_global: bool
    created_at: str
    updated_at: str
    variable_count: int
    workspace_count: int
    variables: list[VariableSetVariable] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Variable management within a set
# ---------------------------------------------------------------------------


class SetVariableRequest(BaseModel):
    key: str
    value: str
    category: str = "terraform"     # "terraform" | "env"
    is_sensitive: bool = False
    is_hcl: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Workspace assignment
# ---------------------------------------------------------------------------


class AssignWorkspaceRequest(BaseModel):
    priority: int = 0               # higher = wins over lower-priority sets


class WorkspaceAssignmentResponse(BaseModel):
    variable_set_id: str
    workspace_id: str
    priority: int
