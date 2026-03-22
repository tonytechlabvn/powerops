"""Project template engine — loads YAML project templates and creates projects from them.

Templates live in templates/projects/*.yaml. Each describes a multi-module project
with variables, providers, roles, and outputs.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "projects"


# ---------------------------------------------------------------------------
# Template listing and retrieval
# ---------------------------------------------------------------------------

def list_project_templates(
    category: str | None = None,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Scan templates/projects/*.yaml, apply optional filters, return metadata list."""
    templates: list[dict[str, Any]] = []

    if not _TEMPLATE_DIR.exists():
        logger.warning("Project templates directory not found: %s", _TEMPLATE_DIR)
        return templates

    for f in sorted(_TEMPLATE_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to parse template %s: %s", f.name, exc)
            continue

        if not isinstance(data, dict):
            continue

        # Apply filters
        if category and data.get("category") != category:
            continue
        if provider and provider not in data.get("providers", []):
            continue

        templates.append({
            "name": data["name"],
            "display_name": data.get("display_name", data["name"]),
            "description": data.get("description", ""),
            "category": data.get("category", ""),
            "complexity": data.get("complexity", ""),
            "providers": data.get("providers", []),
            "tags": data.get("tags", []),
            "module_count": len(data.get("modules", [])),
        })

    return templates


def get_project_template(name: str) -> dict[str, Any] | None:
    """Return full template data for the given template name, or None if not found."""
    path = _TEMPLATE_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to parse template %s: %s", name, exc)
        return None


# ---------------------------------------------------------------------------
# Project creation from template
# ---------------------------------------------------------------------------

async def create_project_from_template(
    template_name: str,
    project_name: str,
    variables: dict[str, Any],
    user_id: str,
    org_id: str | None,
) -> str:
    """Create a Project + modules from a named template.

    Applies caller-supplied variables on top of template defaults.
    Returns the new project_id.

    Raises:
        ValueError: if the template does not exist.
    """
    from backend.db.database import get_session
    from backend.db.models import Project, ProjectMember, ProjectModule

    template = get_project_template(template_name)
    if not template:
        raise ValueError(f"Template not found: {template_name}")

    # Merge caller variables over template defaults
    merged_vars: dict[str, Any] = {}
    for var in template.get("variables", []):
        merged_vars[var["name"]] = var.get("default")
    merged_vars.update(variables)

    # Store full template + merged vars as the project config
    config_payload = dict(template)
    config_payload["applied_variables"] = merged_vars
    config_yaml = yaml.dump(config_payload, default_flow_style=False, allow_unicode=True)

    resolved_name = project_name.strip() or template["name"]

    async with get_session() as session:
        project = Project(
            name=resolved_name,
            description=template.get("description", ""),
            config_yaml=config_yaml,
            org_id=org_id,
            created_by=user_id,
        )
        session.add(project)
        await session.flush()  # get project.id

        # Create modules from template definition
        for m in template.get("modules", []):
            provider = m.get("provider", "")
            session.add(ProjectModule(
                project_id=project.id,
                name=m["name"],
                path=f"modules/{provider}/{m['name']}" if provider else f"modules/{m['name']}",
                provider=provider,
                depends_on=m.get("depends_on", []),
            ))

        # Add creator as workspace-admin
        session.add(ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role_name="workspace-admin",
        ))

        await session.flush()
        project_id: str = project.id

    logger.info(
        "Created project %r (id=%s) from template %r for user %s",
        resolved_name, project_id, template_name, user_id,
    )
    return project_id
