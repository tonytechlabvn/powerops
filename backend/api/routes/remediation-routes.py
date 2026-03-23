"""AI remediation routes for failed terraform operations (Phase 10).

POST /api/workspaces/{workspace_id}/remediate        — diagnose + suggest fixes
POST /api/workspaces/{workspace_id}/remediate/apply  — apply suggested fixes to files
POST /api/jobs/{job_id}/remediate                    — remediate a specific failed job
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["remediation"])


# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

def _load(rel: str, alias: str):
    full = f"backend.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    base = _P(__file__).resolve().parent.parent
    spec = _ilu.spec_from_file_location(full, base / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _schemas():
    return _load("schemas/remediation-schemas.py", "api.schemas.remediation_schemas")


def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _workspace_path(workspace_id: str) -> _P:
    from backend.core.config import get_settings
    settings = get_settings()
    base = _P(settings.working_dir).resolve()
    ws = (base / workspace_id).resolve()
    if not str(ws).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid workspace path")
    if not ws.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found")
    return ws


def _get_engine():
    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    from backend.core.llm import get_llm_client
    engine_mod = load_kebab_module("ai-remediation-engine.py", "ai_remediation_engine")
    cfg = get_settings()
    return engine_mod.AIRemediationEngine(client=get_llm_client(cfg), max_tokens=cfg.ai_max_tokens)


def _remediation_to_response(result, schemas):
    """Convert RemediationResult dataclass to RemediationResponse schema."""
    return schemas.RemediationResponse(
        error_category=schemas.ErrorCategoryResponse(
            type=result.error_category.type,
            is_code_fixable=result.error_category.is_code_fixable,
            severity=result.error_category.severity,
        ),
        root_cause=result.root_cause,
        is_fixable=result.is_fixable,
        fixes=[
            schemas.FileFixResponse(
                file_path=f.file_path,
                original_content=f.original_content,
                fixed_content=f.fixed_content,
                diff_lines=f.diff_lines,
                description=f.description,
            )
            for f in result.fixes
        ],
        explanation=result.explanation,
        confidence=result.confidence,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/workspaces/{workspace_id}/remediate")
async def remediate_workspace(workspace_id: str, request: Request):
    """Diagnose a terraform failure and suggest HCL fixes.

    Returns error classification, root cause, and per-file diffs.
    User must explicitly call /apply to write fixes to disk.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.RemediationRequest(**(await request.json()))
    ws_path = _workspace_path(workspace_id)

    engine = _get_engine()
    result = await engine.diagnose_and_fix(
        error_output=body.error_output,
        workspace_dir=ws_path,
        failed_operation=body.failed_operation,
        plan_json=body.plan_json,
    )
    return _remediation_to_response(result, schemas)


@router.post("/api/workspaces/{workspace_id}/remediate/apply")
async def apply_remediation(workspace_id: str, request: Request):
    """Apply previously suggested fixes to workspace files.

    Requires explicit user action — never called automatically.
    Validates HCL syntax after writing and returns validation results.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.ApplyFixRequest(**(await request.json()))
    ws_path = _workspace_path(workspace_id)

    # Reconstruct FileFix dataclasses from request body
    from backend.core import load_kebab_module
    helpers_mod = load_kebab_module("ai-remediation-helpers.py", "ai_remediation_helpers")

    fixes = [
        helpers_mod.FileFix(
            file_path=f.file_path,
            original_content="",   # not needed for apply
            fixed_content=f.fixed_content,
            diff_lines=[],
            description=f.description,
        )
        for f in body.fixes
    ]

    engine = _get_engine()
    apply_result = await engine.apply_fixes(workspace_dir=ws_path, fixes=fixes)

    return schemas.ApplyFixResponse(
        applied=apply_result.applied,
        failed=apply_result.failed,
        validation_errors=apply_result.validation_errors,
    )


@router.post("/api/jobs/{job_id}/remediate")
async def remediate_job(job_id: str, request: Request):
    """Remediate a specific failed plan/apply job by its ID.

    Fetches error output from the job record and the workspace,
    then runs the same diagnosis as the workspace endpoint.
    """
    _require_auth(request)
    schemas = _schemas()
    body = await request.json()
    workspace_id = body.get("workspace_id", "")
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")

    # Fetch job error from DB
    from backend.db.database import get_session
    from backend.api.services.job_service import JobService
    async with get_session() as session:
        svc = JobService(session)
        job = await svc.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="Job has not failed — nothing to remediate")

    ws_path = _workspace_path(workspace_id)
    error_output = job.error or job.output or "Unknown error"

    engine = _get_engine()
    result = await engine.diagnose_and_fix(
        error_output=error_output,
        workspace_dir=ws_path,
        failed_operation=job.type,
    )
    return _remediation_to_response(result, schemas)
