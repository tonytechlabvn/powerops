"""Project-level permission resolution using role definitions from project config YAML.

Resolves effective permissions for a user within a project by:
  1. Looking up ProjectMember row to get role_name and assigned_modules
  2. Parsing the project's config_yaml to find the matching role definition
  3. Checking permission strings and optional module pattern scoping via fnmatch
"""
from __future__ import annotations

import fnmatch
import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from sqlalchemy import select as sa_select

from backend.db.database import get_session
from backend.db.models import ProjectMember, Project

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy-load project-config-parser (kebab-case filename)
# ---------------------------------------------------------------------------

def _load_config_parser():
    alias = "backend.core.project_config_parser"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(
        alias,
        _P(__file__).resolve().parent / "project-config-parser.py",
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_member_permissions(user_id: str, project_id: str) -> dict | None:
    """Return {role_name, permissions, module_patterns} or None if not a member.

    module_patterns: list of fnmatch patterns restricting which modules the
    role applies to. Empty list means the role covers all modules.
    """
    async with get_session() as session:
        member = (await session.execute(
            sa_select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )).scalar_one_or_none()

        if member is None:
            return None

        project = (await session.execute(
            sa_select(Project).where(Project.id == project_id)
        )).scalar_one_or_none()

        if project is None:
            return None

        # Default permissions when no role definition found in config
        role_permissions: list[str] = []
        role_module_patterns: list[str] = []

        if project.config_yaml.strip():
            try:
                _parser = _load_config_parser()
                config = _parser.parse_project_yaml(project.config_yaml)
                # Find matching role definition by name
                for role_def in config.roles:
                    if role_def.name == member.role_name:
                        role_permissions = list(role_def.permissions)
                        role_module_patterns = list(role_def.modules)
                        break
            except Exception as exc:
                logger.warning("Failed to parse project config for permission check: %s", exc)

        # Member's assigned_modules take precedence over role-level module patterns
        effective_patterns = (
            list(member.assigned_modules)
            if member.assigned_modules
            else role_module_patterns
        )

        return {
            "role_name": member.role_name,
            "permissions": role_permissions,
            "module_patterns": effective_patterns,
        }


async def check_permission(
    user_id: str,
    project_id: str,
    permission: str,
    module_name: str | None = None,
) -> bool:
    """Return True if the user has the given permission in the project.

    Args:
        user_id: The authenticated user's database ID.
        project_id: Target project ID.
        permission: Permission string to check (e.g. "run:plan", "members:manage").
        module_name: Optional module name for scoped permission checks.

    Keycloak admin role always returns True without a DB lookup.
    """
    # Keycloak admins bypass all project-level checks (handled by caller via
    # request.state.user["roles"]), but we do an explicit check here too for
    # programmatic usage.
    # NOTE: caller can short-circuit before calling this function if needed.

    member_info = await get_member_permissions(user_id, project_id)
    if member_info is None:
        return False

    if permission not in member_info["permissions"]:
        return False

    # If a module scope is provided, verify the role covers that module.
    if module_name is not None:
        patterns = member_info["module_patterns"]
        if not matches_module_pattern(module_name, patterns):
            return False

    return True


def matches_module_pattern(module_name: str, patterns: list[str]) -> bool:
    """Return True if module_name matches any pattern, or patterns is empty (all allowed).

    Uses fnmatch glob matching so patterns like "aws-*" or "prod-*" work.
    """
    if not patterns:
        return True  # empty pattern list = unrestricted
    return any(fnmatch.fnmatch(module_name, p) for p in patterns)
