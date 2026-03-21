"""Template management routes.

GET  /api/templates              — list all templates (optional ?provider= filter)
GET  /api/templates/{name:path}  — get a single template's details
POST /api/templates/render       — render HCL from template + variables
POST /api/templates/validate     — validate raw HCL string
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.core import template_engine, hcl_validator
from backend.core.models import Template
from backend.api.schemas.request_schemas import RenderTemplateRequest, ValidateHCLRequest
from backend.api.schemas.response_schemas import (
    RenderResponse,
    TemplateListResponse,
    ValidateResponse,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    provider: str | None = Query(
        None, description="Filter by provider (aws | proxmox | azure | gcp)"
    ),
) -> TemplateListResponse:
    """Return all available templates, optionally filtered by provider."""
    templates = template_engine.list_templates(provider=provider)
    return TemplateListResponse(templates=templates, total=len(templates))


@router.get("/{name:path}", response_model=Template)
async def get_template(name: str) -> Template:
    """Return a single template's metadata and variable schema."""
    # TemplateError raised here is caught by global handler -> 404
    return template_engine.get_template(name)


@router.post("/render", response_model=RenderResponse)
async def render_template(body: RenderTemplateRequest) -> RenderResponse:
    """Render a Jinja2 template with supplied variables into HCL."""
    hcl = template_engine.render_template(body.name, body.variables)
    return RenderResponse(name=body.name, hcl=hcl, variables_applied=body.variables)


@router.post("/validate", response_model=ValidateResponse)
async def validate_hcl(body: ValidateHCLRequest) -> ValidateResponse:
    """Validate raw HCL syntax and check resource whitelist."""
    result = hcl_validator.validate_full(body.hcl)
    return ValidateResponse(result=result)
