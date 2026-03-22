"""Project multi-module execution endpoints.

POST /api/projects/{id}/scaffold          — generate module dirs + starter .tf files
POST /api/projects/{id}/plan              — plan all modules in dependency order
POST /api/projects/{id}/apply             — apply all modules in dependency order
POST /api/projects/{id}/modules/{mid}/plan  — plan a single module
POST /api/projects/{id}/modules/{mid}/apply — apply a single module
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
import tempfile
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["project-execution"])


# ---------------------------------------------------------------------------
# Kebab-case sibling loaders
# ---------------------------------------------------------------------------


def _load_core(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    core_dir = _P(__file__).resolve().parent.parent.parent / "core"
    spec = _ilu.spec_from_file_location(full, core_dir / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_schema(rel: str, alias: str):
    full = f"backend.api.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Auth helper (mirrors project-routes.py pattern)
# ---------------------------------------------------------------------------


def _require_auth(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if state is None or not isinstance(state, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state


# ---------------------------------------------------------------------------
# Response / Request schemas
# ---------------------------------------------------------------------------


class ModuleRunResult(BaseModel):
    name: str
    status: str
    run_id: str = ""
    error: str = ""


class ProjectExecutionResponse(BaseModel):
    status: str
    modules: list[ModuleRunResult] = []
    errors: list[str] = []


class ScaffoldResponse(BaseModel):
    status: str
    project_dir: str
    module_count: int


# ---------------------------------------------------------------------------
# Helper: resolve module by id within a project
# ---------------------------------------------------------------------------


async def _get_module_or_404(project_id: str, module_id: str):
    """Load a ProjectModule belonging to the given project, raise 404 if missing."""
    from backend.db.database import get_session
    from backend.db.models import ProjectModule
    from sqlalchemy import select as sa_select

    async with get_session() as session:
        mod = (await session.execute(
            sa_select(ProjectModule).where(
                ProjectModule.id == module_id,
                ProjectModule.project_id == project_id,
            )
        )).scalar_one_or_none()

    if mod is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return mod


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{project_id}/scaffold", response_model=ScaffoldResponse, status_code=202)
async def scaffold_project(project_id: str, request: Request):
    """Generate project directory structure with starter .tf files for each module."""
    _require_auth(request)

    _scaffolder = _load_core("project-scaffolder.py", "project_scaffolder")

    try:
        # Use system temp dir as base — callers can customise via config later
        base_dir = _P(tempfile.gettempdir()) / "terrabot-projects"
        base_dir.mkdir(parents=True, exist_ok=True)

        project_root = await _scaffolder.scaffold_project(
            project_id=project_id,
            base_dir=base_dir,
        )

        # Count generated module dirs (one level below modules/{provider}/)
        module_dirs = [p for p in project_root.rglob("main.tf")]
        return ScaffoldResponse(
            status="scaffolded",
            project_dir=str(project_root),
            module_count=len(module_dirs),
        )

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Scaffold failed for project %s", project_id)
        raise HTTPException(status_code=500, detail=f"Scaffold error: {exc}")


@router.post("/{project_id}/plan", response_model=ProjectExecutionResponse, status_code=202)
async def plan_all_modules(project_id: str, request: Request):
    """Run terraform plan across all project modules in dependency order."""
    user = _require_auth(request)

    _executor = _load_core("project-executor.py", "project_executor")

    try:
        result = await _executor.execute_project(
            project_id=project_id,
            operation="plan",
            user_id=user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Plan-all failed for project %s", project_id)
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}")

    return ProjectExecutionResponse(
        status=result["status"],
        modules=[ModuleRunResult(**m) for m in result["modules"]],
        errors=result["errors"],
    )


@router.post("/{project_id}/apply", response_model=ProjectExecutionResponse, status_code=202)
async def apply_all_modules(project_id: str, request: Request):
    """Run terraform apply across all project modules in dependency order."""
    user = _require_auth(request)

    _executor = _load_core("project-executor.py", "project_executor")

    try:
        result = await _executor.execute_project(
            project_id=project_id,
            operation="apply",
            user_id=user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Apply-all failed for project %s", project_id)
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}")

    return ProjectExecutionResponse(
        status=result["status"],
        modules=[ModuleRunResult(**m) for m in result["modules"]],
        errors=result["errors"],
    )


@router.post(
    "/{project_id}/modules/{module_id}/plan",
    response_model=ProjectExecutionResponse,
    status_code=202,
)
async def plan_single_module(project_id: str, module_id: str, request: Request):
    """Run terraform plan for a single module (respects dependency ordering)."""
    user = _require_auth(request)

    mod = await _get_module_or_404(project_id, module_id)

    _executor = _load_core("project-executor.py", "project_executor")

    try:
        result = await _executor.execute_project(
            project_id=project_id,
            operation="plan",
            user_id=user["user_id"],
            module_names=[mod.name],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Plan failed for module %s in project %s", module_id, project_id)
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}")

    return ProjectExecutionResponse(
        status=result["status"],
        modules=[ModuleRunResult(**m) for m in result["modules"]],
        errors=result["errors"],
    )


@router.post(
    "/{project_id}/modules/{module_id}/apply",
    response_model=ProjectExecutionResponse,
    status_code=202,
)
async def apply_single_module(project_id: str, module_id: str, request: Request):
    """Run terraform apply for a single module."""
    user = _require_auth(request)

    mod = await _get_module_or_404(project_id, module_id)

    _executor = _load_core("project-executor.py", "project_executor")

    try:
        result = await _executor.execute_project(
            project_id=project_id,
            operation="apply",
            user_id=user["user_id"],
            module_names=[mod.name],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Apply failed for module %s in project %s", module_id, project_id)
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}")

    return ProjectExecutionResponse(
        status=result["status"],
        modules=[ModuleRunResult(**m) for m in result["modules"]],
        errors=result["errors"],
    )
