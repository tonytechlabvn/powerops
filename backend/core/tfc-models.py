"""Pydantic models for HCP Terraform Cloud (TFC) API v2 JSON:API responses.

TFC uses the JSON:API envelope format:
  { "data": { "id": "...", "type": "...", "attributes": {...}, "relationships": {...} } }

The parse_jsonapi* helpers flatten that envelope into plain dicts before
constructing Pydantic models, keeping consumers free of JSON:API awareness.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# JSON:API envelope helpers
# ---------------------------------------------------------------------------


def parse_jsonapi(data: dict) -> dict:
    """Flatten a single JSON:API resource envelope to attribute dict + id."""
    resource = data.get("data", data)  # tolerate pre-extracted resource
    attrs: dict = resource.get("attributes", {})
    result = {"id": resource.get("id", ""), **attrs}
    # Hoist relationship ids that are commonly needed
    rels: dict = resource.get("relationships", {})
    for rel_name, rel_body in rels.items():
        rel_data = rel_body.get("data") if isinstance(rel_body, dict) else None
        if isinstance(rel_data, dict):
            result[f"{rel_name}_id"] = rel_data.get("id", "")
    return result


def parse_jsonapi_list(data: dict) -> list[dict]:
    """Flatten a JSON:API list response to a list of flattened attribute dicts."""
    items = data.get("data", [])
    return [parse_jsonapi({"data": item}) for item in items]


# ---------------------------------------------------------------------------
# TFC domain models
# ---------------------------------------------------------------------------


class TFCOrg(BaseModel):
    """Minimal representation of a TFC Organization."""

    id: str  # org name (same as id in TFC)
    name: str = ""
    email: str = ""
    created_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}

    @classmethod
    def from_jsonapi(cls, data: dict) -> "TFCOrg":
        flat = parse_jsonapi(data)
        return cls(
            id=flat.get("id", flat.get("name", "")),
            name=flat.get("name", flat.get("id", "")),
            email=flat.get("email", ""),
            created_at=flat.get("created-at"),
        )


class TFCWorkspace(BaseModel):
    """TFC Workspace resource."""

    id: str
    name: str = ""
    org_name: str = ""
    execution_mode: str = "remote"
    auto_apply: bool = False
    locked: bool = False
    terraform_version: str = ""
    working_directory: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_jsonapi(cls, data: dict, org_name: str = "") -> "TFCWorkspace":
        flat = parse_jsonapi(data)
        return cls(
            id=flat.get("id", ""),
            name=flat.get("name", ""),
            org_name=org_name,
            execution_mode=flat.get("execution-mode", "remote"),
            auto_apply=flat.get("auto-apply", False),
            locked=flat.get("locked", False),
            terraform_version=flat.get("terraform-version", ""),
            working_directory=flat.get("working-directory", ""),
            created_at=flat.get("created-at"),
            updated_at=flat.get("updated-at"),
        )


class TFCVariable(BaseModel):
    """TFC Workspace Variable."""

    id: str
    workspace_id: str = ""
    key: str = ""
    value: str = ""
    description: str = ""
    category: str = "terraform"  # terraform | env
    sensitive: bool = False
    hcl: bool = False

    @classmethod
    def from_jsonapi(cls, data: dict) -> "TFCVariable":
        flat = parse_jsonapi(data)
        return cls(
            id=flat.get("id", ""),
            workspace_id=flat.get("workspace_id", ""),
            key=flat.get("key", ""),
            value=flat.get("value", ""),
            description=flat.get("description", ""),
            category=flat.get("category", "terraform"),
            sensitive=flat.get("sensitive", False),
            hcl=flat.get("hcl", False),
        )


class TFCPlan(BaseModel):
    """TFC Plan resource (embedded in a Run)."""

    id: str
    status: str = ""
    log_read_url: str = ""
    resource_additions: int = 0
    resource_changes: int = 0
    resource_destructions: int = 0

    @classmethod
    def from_jsonapi(cls, data: dict) -> "TFCPlan":
        flat = parse_jsonapi(data)
        return cls(
            id=flat.get("id", ""),
            status=flat.get("status", ""),
            log_read_url=flat.get("log-read-url", ""),
            resource_additions=flat.get("resource-additions", 0),
            resource_changes=flat.get("resource-changes", 0),
            resource_destructions=flat.get("resource-destructions", 0),
        )


class TFCRun(BaseModel):
    """TFC Run resource."""

    id: str
    status: str = ""
    message: str = ""
    auto_apply: bool = False
    is_destroy: bool = False
    workspace_id: str = ""
    plan_id: str = ""
    created_at: Optional[datetime] = None
    status_timestamps: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_jsonapi(cls, data: dict) -> "TFCRun":
        flat = parse_jsonapi(data)
        return cls(
            id=flat.get("id", ""),
            status=flat.get("status", ""),
            message=flat.get("message", ""),
            auto_apply=flat.get("auto-apply", False),
            is_destroy=flat.get("is-destroy", False),
            workspace_id=flat.get("workspace_id", ""),
            plan_id=flat.get("plan_id", ""),
            created_at=flat.get("created-at"),
            status_timestamps=flat.get("status-timestamps", {}),
        )
