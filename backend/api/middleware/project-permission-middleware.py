"""FastAPI dependency for project-level permission enforcement.

Usage in a route:
    from backend.api.middleware import project_permission_middleware as _ppm
    ...
    async def my_route(
        project_id: str,
        request: Request,
        _: None = Depends(_ppm.require_project_permission("run:plan")),
    ): ...

Or with module scoping:
    _: None = Depends(_ppm.require_project_permission("run:apply", module_param="module_id"))

Keycloak users with the "admin" role bypass all project checks.
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P
from typing import Callable

from fastapi import Depends, HTTPException, Request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy-load project-permission-checker (kebab-case filename)
# ---------------------------------------------------------------------------

def _load_checker():
    alias = "backend.core.project_permission_checker"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(
        alias,
        _P(__file__).resolve().parent.parent.parent / "core" / "project-permission-checker.py",
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------

def require_project_permission(
    permission: str,
    project_param: str = "project_id",
    module_param: str | None = None,
) -> Callable:
    """Return a FastAPI Depends that raises 403 when the check fails.

    Args:
        permission: The permission string to check (e.g. "run:plan").
        project_param: Name of the path parameter holding the project ID.
        module_param: Optional path/query parameter holding a module name for
                      scoped checks. When None, no module scoping is applied.
    """

    async def _check(request: Request) -> None:
        state = getattr(request.state, "user", None)
        if state is None or not isinstance(state, dict):
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id: str | None = state.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Keycloak admin role bypasses project-level checks
        if "admin" in state.get("roles", []):
            return

        project_id: str | None = request.path_params.get(project_param)
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail=f"Missing path parameter '{project_param}'",
            )

        # Resolve optional module name from path params or query params
        module_name: str | None = None
        if module_param:
            module_name = (
                request.path_params.get(module_param)
                or request.query_params.get(module_param)
            )

        _checker = _load_checker()
        allowed = await _checker.check_permission(
            user_id=user_id,
            project_id=project_id,
            permission=permission,
            module_name=module_name,
        )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' denied on project '{project_id}'",
            )

    return Depends(_check)
