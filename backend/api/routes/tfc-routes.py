"""HCP Terraform Cloud management endpoints.

All routes are scoped under /api/projects/{project_id}/tfc.

POST   /setup            — store TFC org + token for this project
GET    /workspaces       — list TFC workspaces in the configured org
POST   /sync             — sync project modules → TFC workspaces
POST   /variables        — push variables to a specific TFC workspace
POST   /runs             — trigger a new run
POST   /runs/{run_id}/apply   — confirm (apply) a pending run
POST   /runs/{run_id}/discard — discard a pending run
GET    /runs             — list recent runs for a TFC workspace
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select as sa_select

from backend.core.config import get_settings
from backend.db.database import get_session
from backend.db.models import Project, ProjectCredential, ProjectModule

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/tfc", tags=["tfc"])

# ---------------------------------------------------------------------------
# Lazy module loaders (kebab-case files)
# ---------------------------------------------------------------------------

_SCHEMAS_DIR = _P(__file__).resolve().parent.parent / "schemas"
_CORE_DIR = _P(__file__).resolve().parent.parent.parent / "core"


def _load(path: _P, alias: str):
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(alias, path)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _schemas():
    return _load(_SCHEMAS_DIR / "tfc-schemas.py", "backend.api.schemas.tfc_schemas")


def _client_mod():
    return _load(_CORE_DIR / "tfc-api-client.py", "backend.core.tfc_api_client")


def _sync_mod():
    return _load(_CORE_DIR / "tfc-sync-service.py", "backend.core.tfc_sync_service")


# ---------------------------------------------------------------------------
# Auth / project helpers
# ---------------------------------------------------------------------------


def _require_auth(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if not isinstance(state, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state


async def _get_project_or_404(session, project_id: str) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ---------------------------------------------------------------------------
# TFC credential storage (in ProjectCredential with provider="tfc")
# ---------------------------------------------------------------------------

_TFC_PROVIDER = "tfc"


async def _get_tfc_cred(session, project_id: str) -> dict:
    """Return stored TFC credentials dict or raise 400 if not configured."""
    import json

    row = (await session.execute(
        sa_select(ProjectCredential).where(
            ProjectCredential.project_id == project_id,
            ProjectCredential.provider == _TFC_PROVIDER,
        )
    )).scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=400,
            detail="TFC not configured for this project. Call POST /tfc/setup first.",
        )

    # Credential data is stored as-is (JSON string) — decrypt if encryption key set
    raw = row.credential_data
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode()

    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupt TFC credential data")


async def _save_tfc_cred(session, project_id: str, org_name: str, api_token: str) -> None:
    """Upsert TFC credential record for this project."""
    import json

    payload = json.dumps({"org_name": org_name, "api_token": api_token})

    existing = (await session.execute(
        sa_select(ProjectCredential).where(
            ProjectCredential.project_id == project_id,
            ProjectCredential.provider == _TFC_PROVIDER,
        )
    )).scalar_one_or_none()

    if existing:
        existing.credential_data = payload
        session.add(existing)
    else:
        cred = ProjectCredential(
            project_id=project_id,
            provider=_TFC_PROVIDER,
            credential_data=payload,
            is_sensitive=True,
            created_by="api",
        )
        session.add(cred)


def _make_client(cred: dict):
    """Instantiate TFCClient from stored credential dict."""
    _cm = _client_mod()
    settings = get_settings()
    return _cm.TFCClient(
        token=cred["api_token"],
        base_url=settings.tfc_base_url or "https://app.terraform.io",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/setup")
async def tfc_setup(project_id: str, request: Request):
    """Store TFC organisation and API token for this project."""
    _require_auth(request)
    _s = _schemas()
    body = _s.TFCSetupRequest(**(await request.json()))

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        await _save_tfc_cred(session, project_id, body.org_name, body.api_token)

    return _s.TFCSetupResponse(project_id=project_id, org_name=body.org_name)


@router.get("/workspaces")
async def list_tfc_workspaces(project_id: str, request: Request):
    """List TFC workspaces in the configured organisation."""
    _require_auth(request)
    _s = _schemas()
    _cm = _client_mod()

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

    try:
        client = _make_client(cred)
        workspaces = await client.list_workspaces(cred["org_name"])
    except _cm.TFCAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return [
        _s.TFCWorkspaceResponse(
            id=ws.id,
            name=ws.name,
            org_name=ws.org_name,
            execution_mode=ws.execution_mode,
            auto_apply=ws.auto_apply,
            locked=ws.locked,
            terraform_version=ws.terraform_version,
            working_directory=ws.working_directory,
            created_at=ws.created_at,
        )
        for ws in workspaces
    ]


@router.post("/sync")
async def sync_to_tfc(project_id: str, request: Request):
    """Create or reconcile TFC workspaces for all active project modules."""
    _require_auth(request)
    _s = _schemas()
    _sm = _sync_mod()
    _cm = _client_mod()

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

        # Load active modules
        modules_rows = (await session.execute(
            sa_select(ProjectModule).where(
                ProjectModule.project_id == project_id,
                ProjectModule.status != "removed",
            )
        )).scalars().all()

    modules = [
        {"name": m.name, "provider": m.provider, "path": m.path}
        for m in modules_rows
    ]

    try:
        result = await _sm.sync_project_to_tfc(
            project_id=project_id,
            tfc_token=cred["api_token"],
            org_name=cred["org_name"],
            modules=modules,
        )
    except (RuntimeError, _cm.TFCAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return _s.TFCSyncResponse(
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        total_modules=len(modules),
    )


@router.post("/variables")
async def push_tfc_variables(project_id: str, request: Request):
    """Push variables to a specific TFC workspace."""
    _require_auth(request)
    _s = _schemas()
    _sm = _sync_mod()
    _cm = _client_mod()

    body = _s.TFCPushVariablesRequest(**(await request.json()))

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

    vars_list = [v.model_dump() for v in body.variables]

    try:
        result = await _sm.push_variables(
            ws_id=body.workspace_id,
            vars_list=vars_list,
            tfc_token=cred["api_token"],
        )
    except (RuntimeError, _cm.TFCAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return _s.TFCPushVariablesResponse(
        workspace_id=body.workspace_id,
        created=result["created"],
        updated=result["updated"],
    )


@router.post("/runs")
async def trigger_run(project_id: str, request: Request):
    """Trigger a new Terraform run in TFC."""
    _require_auth(request)
    _s = _schemas()
    _cm = _client_mod()

    body = _s.TFCRunRequest(**(await request.json()))

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

    try:
        client = _make_client(cred)
        run = await client.create_run(
            ws_id=body.workspace_id,
            message=body.message,
            auto_apply=body.auto_apply,
        )
    except _cm.TFCAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return _s.TFCRunResponse(
        id=run.id,
        status=run.status,
        message=run.message,
        auto_apply=run.auto_apply,
        is_destroy=run.is_destroy,
        workspace_id=run.workspace_id,
        created_at=run.created_at,
    )


@router.post("/runs/{run_id}/apply")
async def apply_run(project_id: str, run_id: str, request: Request):
    """Confirm and apply a run awaiting confirmation."""
    _require_auth(request)
    _s = _schemas()
    _cm = _client_mod()

    # Parse optional comment body (may be empty)
    try:
        raw = await request.json()
        body = _s.TFCRunActionRequest(**raw)
    except Exception:
        body = _s.TFCRunActionRequest()

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

    try:
        client = _make_client(cred)
        await client.apply_run(run_id=run_id, comment=body.comment)
    except _cm.TFCAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return {"run_id": run_id, "action": "apply", "status": "accepted"}


@router.post("/runs/{run_id}/discard")
async def discard_run(project_id: str, run_id: str, request: Request):
    """Discard a run awaiting confirmation."""
    _require_auth(request)
    _s = _schemas()
    _cm = _client_mod()

    try:
        raw = await request.json()
        body = _s.TFCRunActionRequest(**raw)
    except Exception:
        body = _s.TFCRunActionRequest()

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

    try:
        client = _make_client(cred)
        await client.discard_run(run_id=run_id, comment=body.comment)
    except _cm.TFCAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return {"run_id": run_id, "action": "discard", "status": "accepted"}


@router.get("/runs")
async def list_runs(
    project_id: str,
    request: Request,
    workspace_id: str = Query(..., description="TFC workspace ID (ws-xxxx)"),
):
    """List recent runs for a TFC workspace."""
    _require_auth(request)
    _s = _schemas()
    _cm = _client_mod()

    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        cred = await _get_tfc_cred(session, project_id)

    try:
        client = _make_client(cred)
        runs = await client.list_runs(ws_id=workspace_id)
    except _cm.TFCAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return [
        _s.TFCRunResponse(
            id=r.id,
            status=r.status,
            message=r.message,
            auto_apply=r.auto_apply,
            is_destroy=r.is_destroy,
            workspace_id=r.workspace_id,
            created_at=r.created_at,
        )
        for r in runs
    ]
