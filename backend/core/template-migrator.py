"""Template Migrator — convert YAML project templates into registry modules + stack templates.

Reads templates from templates/projects/*.yaml and creates:
  1. A RegistryModule + RegistryModuleVersion (with synthetic zip archive)
  2. A StackTemplate referencing those modules
This is a one-time admin operation; existing templates remain intact.
"""
from __future__ import annotations

import importlib.util as _ilu
import io
import json
import logging
import sys as _sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "projects"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class MigrationResult:
    template_name: str
    success: bool
    stack_template_id: str | None = None
    modules_created: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Lazy loaders
# ---------------------------------------------------------------------------

def _load_manager():
    alias = "backend.core.module_registry_manager"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(
        alias, Path(__file__).resolve().parent / "module-registry-manager.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Migrator
# ---------------------------------------------------------------------------

class TemplateMigrator:
    """Converts YAML project templates to registry modules + stack templates."""

    async def migrate_all(
        self, session: AsyncSession, org_id: str, user_id: str
    ) -> list[MigrationResult]:
        """Migrate every template in templates/projects/."""
        results: list[MigrationResult] = []
        if not _TEMPLATE_DIR.exists():
            logger.warning("Template directory not found: %s", _TEMPLATE_DIR)
            return results

        for yaml_file in sorted(_TEMPLATE_DIR.glob("*.yaml")):
            result = await self.migrate_template(
                session, yaml_file.stem, org_id, user_id
            )
            results.append(result)
        return results

    async def migrate_template(
        self,
        session: AsyncSession,
        template_name: str,
        org_id: str,
        user_id: str,
    ) -> MigrationResult:
        """Convert a single YAML template into a registry module + stack template."""
        yaml_path = _TEMPLATE_DIR / f"{template_name}.yaml"
        if not yaml_path.exists():
            return MigrationResult(
                template_name=template_name,
                success=False,
                error=f"Template file not found: {yaml_path}",
            )

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return MigrationResult(
                template_name=template_name, success=False, error=f"YAML parse error: {exc}"
            )

        if not isinstance(data, dict):
            return MigrationResult(
                template_name=template_name, success=False, error="Template is not a YAML dict"
            )

        try:
            stack_id, modules_count = await self._do_migrate(
                session, data, template_name, org_id, user_id
            )
            return MigrationResult(
                template_name=template_name,
                success=True,
                stack_template_id=stack_id,
                modules_created=modules_count,
            )
        except Exception as exc:
            logger.exception("Migration failed for template %s", template_name)
            return MigrationResult(
                template_name=template_name, success=False, error=str(exc)
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _do_migrate(
        self,
        session: AsyncSession,
        data: dict[str, Any],
        template_name: str,
        org_id: str,
        user_id: str,
    ) -> tuple[str, int]:
        """Returns (stack_template_id, modules_created_count)."""
        from backend.db.models import StackTemplate  # type: ignore[attr-defined]

        manager_mod = _load_manager()
        manager = manager_mod.ModuleRegistryManager()

        namespace = "migrated"
        provider = _detect_provider(data)
        modules_raw: list[dict] = data.get("modules", [])
        variables_raw: list[dict] = data.get("variables", [])

        # Publish each module from the template
        stack_modules: list[dict] = []
        modules_created = 0

        for mod_def in modules_raw:
            mod_name = _slug(mod_def.get("name", template_name))
            archive_bytes = _create_synthetic_archive(mod_def, variables_raw)

            # publish_module may 409 if already exists; skip gracefully
            try:
                reg_module = await manager.publish_module(
                    session,
                    org_id=org_id,
                    namespace=namespace,
                    name=mod_name,
                    provider=provider,
                    description=mod_def.get("description", data.get("description", "")),
                    tags=data.get("tags", []),
                    user_id=user_id,
                )
                await manager.publish_version(
                    session,
                    module_id=reg_module.id,
                    version="1.0.0",
                    archive_bytes=archive_bytes,
                    user_id=user_id,
                )
                modules_created += 1
                source = f"{namespace}/{mod_name}/{provider}"
            except Exception as exc:
                logger.warning("Skipping module %s: %s", mod_name, exc)
                source = f"{namespace}/{mod_name}/{provider}"

            stack_modules.append({
                "name": mod_name,
                "source": source,
                "version": "1.0.0",
                "variables": {v["name"]: f'${{var.{v["name"]}}}' for v in variables_raw},
                "depends_on": mod_def.get("depends_on", []),
            })

        # Build stack definition
        stack_vars = [
            {"name": v["name"], "type": v.get("type", "string"),
             "description": v.get("description", ""), "default": v.get("default")}
            for v in variables_raw
        ]
        definition = json.dumps({"modules": stack_modules, "variables": stack_vars})

        # Upsert StackTemplate
        from sqlalchemy import select
        existing = (await session.execute(
            select(StackTemplate).where(
                StackTemplate.org_id == org_id,
                StackTemplate.name == template_name,
            )
        )).scalar_one_or_none()

        if existing:
            existing.definition_json = definition
            session.add(existing)
            await session.flush()
            return existing.id, modules_created

        stack = StackTemplate(
            name=template_name,
            description=data.get("description", ""),
            org_id=org_id,
            definition_json=definition,
            tags=data.get("tags", []),
            created_by=user_id,
        )
        session.add(stack)
        await session.flush()
        return stack.id, modules_created


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9-]", "-", name.lower().strip()).strip("-")


def _detect_provider(data: dict) -> str:
    providers = data.get("providers", [])
    if providers:
        return providers[0].lower()
    return "generic"


def _create_synthetic_archive(mod_def: dict, variables: list[dict]) -> bytes:
    """Create a minimal zip archive from a YAML module definition."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Generate variables.tf
        vars_tf = _render_variables_tf(variables)
        zf.writestr("variables.tf", vars_tf)

        # Generate main.tf stub
        source = mod_def.get("source", "")
        main_tf = f'# Migrated from YAML template\n# Original source: {source}\n'
        if mod_def.get("resources"):
            for res in mod_def.get("resources", []):
                rtype = res.get("type", "null_resource")
                rname = res.get("name", "main")
                main_tf += f'\nresource "{rtype}" "{rname}" {{\n}}\n'
        zf.writestr("main.tf", main_tf)

        # README
        readme = f"# {mod_def.get('name', 'module')}\n\nMigrated from YAML template.\n"
        zf.writestr("README.md", readme)

    return buf.getvalue()


def _render_variables_tf(variables: list[dict]) -> str:
    lines: list[str] = []
    for v in variables:
        lines.append(f'variable "{v["name"]}" {{')
        lines.append(f'  type        = {v.get("type", "string")}')
        desc = v.get("description", "")
        if desc:
            lines.append(f'  description = "{desc}"')
        default = v.get("default")
        if default is not None:
            lines.append(f'  default     = {json.dumps(default)}')
        lines.append("}\n")
    return "\n".join(lines)
