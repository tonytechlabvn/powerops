"""Jinja2-based Terraform template engine.

Templates are stored as directories under templates/{provider}/{name}/ with:
  - main.tf.j2       — Jinja2 template producing valid HCL
  - variables.json   — JSON Schema for accepted variables
  - metadata.json    — display name, description, provider, tags
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from backend.core.config import get_settings
from backend.core.exceptions import TemplateError, ValidationError
from backend.core.models import Template, TemplateMetadata, TemplateVariable

logger = logging.getLogger(__name__)

_MAIN_TEMPLATE = "main.tf.j2"
_VARIABLES_FILE = "variables.json"
_METADATA_FILE = "metadata.json"


def _load_json(path: Path) -> dict:
    """Load and parse a JSON file; return empty dict on missing/invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.debug("Could not load %s: %s", path, exc)
        return {}


def _parse_variables(variables_data: list[dict] | dict) -> list[TemplateVariable]:
    """Convert variables.json content into TemplateVariable list."""
    if isinstance(variables_data, dict):
        # Support {name: {type, description, default, required}} shape
        items = [{"name": k, **v} for k, v in variables_data.items()]
    else:
        items = variables_data

    result: list[TemplateVariable] = []
    for item in items:
        result.append(
            TemplateVariable(
                name=item.get("name", ""),
                type=item.get("type", "string"),
                description=item.get("description", ""),
                default=item.get("default"),
                required=item.get("required", item.get("default") is None),
            )
        )
    return result


def _build_jinja_env(template_dir: Path) -> Environment:
    """Create a Jinja2 Environment scoped to a single template directory."""
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _template_root() -> Path:
    """Resolve the configured template root directory."""
    return Path(get_settings().template_dir)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_templates(provider: str | None = None) -> list[Template]:
    """Scan the template directory and return all available templates.

    Args:
        provider: Optional filter (e.g. "aws", "proxmox"). Returns all if None.

    Returns:
        List of Template objects with metadata and variable schema populated.
    """
    root = _template_root()
    if not root.exists():
        logger.warning("Template directory does not exist: %s", root)
        return []

    templates: list[Template] = []

    # Walk provider subdirectories
    for provider_dir in sorted(root.iterdir()):
        if not provider_dir.is_dir():
            continue
        if provider and provider_dir.name != provider:
            continue

        for template_dir in sorted(provider_dir.iterdir()):
            if not template_dir.is_dir():
                continue
            if not (template_dir / _MAIN_TEMPLATE).exists():
                continue  # skip directories without a template file

            try:
                tmpl = get_template(f"{provider_dir.name}/{template_dir.name}")
                templates.append(tmpl)
            except TemplateError as exc:
                logger.warning("Skipping malformed template %s: %s", template_dir, exc)

    return templates


def get_template(name: str) -> Template:
    """Load a single template by its provider/name path.

    Args:
        name: Template identifier in "provider/template-name" format.

    Returns:
        Template object with metadata, variables, and path.

    Raises:
        TemplateError: If the template directory or main file is missing.
    """
    root = _template_root()
    template_dir = root / name

    if not template_dir.is_dir():
        raise TemplateError(f"Template not found: {name}", template_name=name)

    main_file = template_dir / _MAIN_TEMPLATE
    if not main_file.exists():
        raise TemplateError(
            f"Template '{name}' is missing {_MAIN_TEMPLATE}", template_name=name
        )

    raw_meta = _load_json(template_dir / _METADATA_FILE)
    raw_vars = _load_json(template_dir / _VARIABLES_FILE)

    # Derive provider from path if not in metadata
    parts = name.split("/")
    inferred_provider = parts[0] if len(parts) >= 2 else ""

    metadata = TemplateMetadata(
        name=name,
        display_name=raw_meta.get("display_name", template_dir.name),
        description=raw_meta.get("description", ""),
        provider=raw_meta.get("provider", inferred_provider),
        version=raw_meta.get("version", "1.0.0"),
        tags=raw_meta.get("tags", []),
        author=raw_meta.get("author", ""),
    )

    vars_raw = raw_vars.get("variables", raw_vars) if raw_vars else []
    variables = _parse_variables(vars_raw)

    return Template(
        metadata=metadata,
        variables=variables,
        path=str(template_dir.resolve()),
    )


def validate_variables(template: Template, variables: dict[str, Any]) -> list[str]:
    """Validate user-supplied variables against the template schema.

    Args:
        template: Template object from get_template().
        variables: Dict of variable name → value supplied by the user.

    Returns:
        List of error strings. Empty list means validation passed.
    """
    errors: list[str] = []

    for var in template.variables:
        if var.name not in variables:
            if var.required and var.default is None:
                errors.append(f"Required variable '{var.name}' is missing.")
            continue

        value = variables[var.name]

        # Basic type checking
        type_checks: dict[str, type | tuple] = {
            "string": str,
            "number": (int, float),
            "bool": bool,
            "list": list,
            "map": dict,
        }
        expected = type_checks.get(var.type)
        if expected and not isinstance(value, expected):
            errors.append(
                f"Variable '{var.name}' expects type '{var.type}', "
                f"got {type(value).__name__}."
            )

    # Warn about unknown variables (not an error, just informational)
    known = {v.name for v in template.variables}
    for key in variables:
        if key not in known:
            logger.debug("Unknown variable '%s' passed to template '%s'", key, template.metadata.name)

    return errors


def render_template(name: str, variables: dict[str, Any]) -> str:
    """Render a Jinja2 template with the supplied variables.

    Validation is performed before rendering. Raises on missing required
    variables or Jinja2 rendering errors.

    Args:
        name: Template identifier (e.g. "aws/ec2-web-server").
        variables: Dict of variable name → value.

    Returns:
        Rendered HCL string ready to write to a .tf file.

    Raises:
        TemplateError: If template not found or Jinja2 rendering fails.
        ValidationError: If required variables are missing or have wrong types.
    """
    template = get_template(name)

    errors = validate_variables(template, variables)
    if errors:
        raise ValidationError(
            f"Variable validation failed for template '{name}'",
            violations=errors,
        )

    # Merge defaults for omitted optional variables
    merged: dict[str, Any] = {}
    for var in template.variables:
        if var.name in variables:
            merged[var.name] = variables[var.name]
        elif var.default is not None:
            merged[var.name] = var.default

    template_dir = Path(template.path)
    env = _build_jinja_env(template_dir)

    try:
        jinja_tmpl = env.get_template(_MAIN_TEMPLATE)
        rendered = jinja_tmpl.render(**merged)
    except TemplateNotFound:
        raise TemplateError(
            f"Jinja2 template file not found in '{name}'", template_name=name
        )
    except Exception as exc:
        raise TemplateError(
            f"Rendering failed for template '{name}': {exc}", template_name=name
        ) from exc

    logger.debug("Rendered template '%s' (%d chars)", name, len(rendered))
    return rendered
