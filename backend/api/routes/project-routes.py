"""Project CRUD endpoints.

POST   /api/projects                      — create project (from YAML or form)
GET    /api/projects                      — list projects (filtered by org)
GET    /api/projects/{id}                 — get project detail
PATCH  /api/projects/{id}                 — update project
DELETE /api/projects/{id}                 — soft-delete (set archived)
GET    /api/projects/{id}/modules         — list project modules
POST   /api/projects/{id}/members         — add member with role
DELETE /api/projects/{id}/members/{uid}   — remove member
GET    /api/projects/{id}/runs            — list runs
POST   /api/projects/{id}/credentials     — add encrypted credential
GET    /api/projects/{id}/credentials     — list credentials (no raw data)
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select as sa_select
from sqlalchemy.orm import selectinload

from backend.db.database import get_session
from backend.db.models import (
    Project, ProjectCredential, ProjectMember, ProjectModule, ProjectRun, User,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Kebab-case module loaders
# ---------------------------------------------------------------------------

def _load_schema(rel: str, alias: str):
    full = f"backend.api.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _P(__file__).resolve().parent.parent / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_core(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent.parent / "core" / rel
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_schemas = _load_schema("schemas/project-schemas.py", "schemas.project_schemas")

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_auth(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if state is None or not isinstance(state, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return state


async def _require_project_member(session, project_id: str, user: dict) -> ProjectMember | None:
    """Verify user is a member of the project. Returns member or raises 403."""
    member = (await session.execute(
        sa_select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user["user_id"],
        )
    )).scalar_one_or_none()
    # Allow if user has admin role from Keycloak
    if member is None and "admin" not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Not a project member")
    return member


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=_schemas.ProjectResponse, status_code=201)
async def create_project(body: _schemas.CreateProjectRequest, request: Request):
    """Create a new project. Optionally parses config_yaml to auto-create modules."""
    user = _require_auth(request)

    modules_to_create: list[dict] = []
    if body.config_yaml.strip():
        _parser = _load_core("project-config-parser.py", "project_config_parser")
        try:
            config = _parser.parse_project_yaml(body.config_yaml)
        except _parser.ProjectConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        # Use parsed name if body.name is generic
        if not body.name.strip():
            body.name = config.name
        modules_to_create = [
            {"name": m.name, "path": m.path, "provider": m.provider, "depends_on": m.depends_on}
            for m in config.modules
        ]

    async with get_session() as session:
        # Check duplicate name within org
        existing = (await session.execute(
            sa_select(Project).where(
                Project.name == body.name,
                Project.org_id == user.get("org_id"),
                Project.status != "archived",
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Project name already exists")

        project = Project(
            name=body.name,
            description=body.description,
            config_yaml=body.config_yaml,
            org_id=user.get("org_id"),
            created_by=user["user_id"],
        )
        session.add(project)
        await session.flush()

        # Auto-create modules from config_yaml
        for m in modules_to_create:
            session.add(ProjectModule(
                project_id=project.id,
                name=m["name"],
                path=m["path"],
                provider=m["provider"],
                depends_on=m["depends_on"],
            ))

        # Auto-add creator as workspace-admin
        session.add(ProjectMember(
            project_id=project.id,
            user_id=user["user_id"],
            role_name="workspace-admin",
        ))
        await session.flush()

        return _project_to_response(project)


@router.get("", response_model=list[_schemas.ProjectResponse])
async def list_projects(request: Request):
    """List all non-archived projects visible to the user."""
    user = _require_auth(request)
    async with get_session() as session:
        q = sa_select(Project).where(Project.status != "archived")
        org_id = user.get("org_id")
        # Always filter by org — users without org see no projects
        q = q.where(Project.org_id == org_id)
        q = q.order_by(Project.updated_at.desc())
        projects = (await session.execute(q)).scalars().all()
        return [_project_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=_schemas.ProjectDetailResponse)
async def get_project(project_id: str, request: Request):
    """Get project with modules, members, and recent runs."""
    user = _require_auth(request)
    async with get_session() as session:
        project = await _get_project_or_404(session, project_id)
        return _project_detail_response(project)


@router.patch("/{project_id}", response_model=_schemas.ProjectDetailResponse)
async def update_project(project_id: str, body: _schemas.UpdateProjectRequest, request: Request):
    """Update project fields."""
    user = _require_auth(request)
    async with get_session() as session:
        await _require_project_member(session, project_id, user)
        project = await _get_project_or_404(session, project_id)

        if body.name is not None:
            project.name = body.name
        if body.description is not None:
            project.description = body.description
        if body.status is not None:
            project.status = body.status
        if body.config_yaml is not None:
            project.config_yaml = body.config_yaml
            # Re-parse and sync modules if YAML changed
            if body.config_yaml.strip():
                _parser = _load_core("project-config-parser.py", "project_config_parser")
                try:
                    config = _parser.parse_project_yaml(body.config_yaml)
                except _parser.ProjectConfigError as e:
                    raise HTTPException(status_code=400, detail=str(e))
                await _sync_modules(session, project, config.modules)

        session.add(project)
        await session.flush()
        # Refresh relationships
        project = await _get_project_or_404(session, project_id)
        return _project_detail_response(project)


@router.delete("/{project_id}", status_code=204)
async def archive_project(project_id: str, request: Request):
    """Soft-delete: set project status to archived."""
    user = _require_auth(request)
    async with get_session() as session:
        await _require_project_member(session, project_id, user)
        project = await _get_project_or_404(session, project_id)
        project.status = "archived"
        session.add(project)


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

@router.get("/{project_id}/modules", response_model=list[_schemas.ProjectModuleResponse])
async def list_modules(project_id: str, request: Request):
    _require_auth(request)
    async with get_session() as session:
        project = await _get_project_or_404(session, project_id)
        return [_module_response(m) for m in project.modules]


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@router.post("/{project_id}/members", response_model=_schemas.ProjectMemberResponse, status_code=201)
async def add_member(project_id: str, body: _schemas.AddMemberRequest, request: Request):
    user = _require_auth(request)
    async with get_session() as session:
        await _require_project_member(session, project_id, user)
        await _get_project_or_404(session, project_id)

        # Verify user exists
        user = (await session.execute(
            sa_select(User).where(User.id == body.user_id)
        )).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        # Check not already a member
        existing = (await session.execute(
            sa_select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == body.user_id,
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="User already a member")

        member = ProjectMember(
            project_id=project_id,
            user_id=body.user_id,
            role_name=body.role_name,
            assigned_modules=body.assigned_modules,
        )
        session.add(member)
        await session.flush()
        return _member_response(member, user)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(project_id: str, user_id: str, request: Request):
    user = _require_auth(request)
    async with get_session() as session:
        await _require_project_member(session, project_id, user)
        member = (await session.execute(
            sa_select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        await session.delete(member)


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.get("/{project_id}/runs", response_model=list[_schemas.ProjectRunResponse])
async def list_runs(project_id: str, request: Request):
    _require_auth(request)
    async with get_session() as session:
        await _get_project_or_404(session, project_id)
        runs = (await session.execute(
            sa_select(ProjectRun)
            .where(ProjectRun.project_id == project_id)
            .options(selectinload(ProjectRun.module))
            .order_by(ProjectRun.started_at.desc())
            .limit(50)
        )).scalars().all()
        return [_run_response(r) for r in runs]


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

@router.post("/{project_id}/credentials", response_model=_schemas.ProjectCredentialResponse, status_code=201)
async def add_credential(project_id: str, body: _schemas.AddCredentialRequest, request: Request):
    """Store encrypted provider credentials for a project."""
    user = _require_auth(request)
    async with get_session() as session:
        await _require_project_member(session, project_id, user)
        await _get_project_or_404(session, project_id)

        # Encrypt credential data
        _enc = _load_core("state-encryption.py", "state_encryption")
        from backend.core.config import get_settings
        s = get_settings()
        if not s.state_encryption_key:
            raise HTTPException(status_code=500, detail="Encryption key not configured")

        import base64
        key = base64.b64decode(s.state_encryption_key)
        encrypted = _enc.encrypt_state(body.credential_json.encode(), key)

        cred = ProjectCredential(
            project_id=project_id,
            provider=body.provider,
            credential_data=encrypted,
            created_by=user["user_id"],
        )
        session.add(cred)
        await session.flush()
        return _schemas.ProjectCredentialResponse(
            id=cred.id,
            provider=cred.provider,
            is_sensitive=cred.is_sensitive,
            created_by=cred.created_by,
            created_at=cred.created_at,
        )


@router.get("/{project_id}/credentials", response_model=list[_schemas.ProjectCredentialResponse])
async def list_credentials(project_id: str, request: Request):
    """List credentials metadata — never returns raw data."""
    _require_auth(request)
    async with get_session() as session:
        project = await _get_project_or_404(session, project_id)
        return [
            _schemas.ProjectCredentialResponse(
                id=c.id, provider=c.provider, is_sensitive=c.is_sensitive,
                created_by=c.created_by, created_at=c.created_at,
            )
            for c in project.credentials
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_project_or_404(session, project_id: str) -> Project:
    project = (await session.execute(
        sa_select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.modules),
            selectinload(Project.members).selectinload(ProjectMember.user),
            selectinload(Project.credentials),
            selectinload(Project.runs).selectinload(ProjectRun.module),
        )
    )).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _project_to_response(p: Project) -> _schemas.ProjectResponse:
    return _schemas.ProjectResponse(
        id=p.id, name=p.name, description=p.description, status=p.status,
        created_by=p.created_by, created_at=p.created_at, updated_at=p.updated_at,
        module_count=len(p.modules) if p.modules else 0,
        member_count=len(p.members) if p.members else 0,
    )


def _project_detail_response(p: Project) -> _schemas.ProjectDetailResponse:
    return _schemas.ProjectDetailResponse(
        id=p.id, name=p.name, description=p.description,
        config_yaml=p.config_yaml, status=p.status, org_id=p.org_id,
        created_by=p.created_by, created_at=p.created_at, updated_at=p.updated_at,
        modules=[_module_response(m) for m in (p.modules or []) if m.status != "removed"],
        members=[_member_response(m, m.user) for m in (p.members or [])],
        runs=[_run_response(r) for r in (p.runs or [])],
    )


def _module_response(m: ProjectModule) -> _schemas.ProjectModuleResponse:
    return _schemas.ProjectModuleResponse(
        id=m.id, name=m.name, path=m.path, provider=m.provider,
        depends_on=m.depends_on or [], status=m.status, last_run_id=m.last_run_id,
    )


def _member_response(m: ProjectMember, user: User | None = None) -> _schemas.ProjectMemberResponse:
    return _schemas.ProjectMemberResponse(
        user_id=m.user_id, role_name=m.role_name,
        assigned_modules=m.assigned_modules or [],
        joined_at=m.joined_at,
        user_email=user.email if user else "",
        user_name=user.name if user else "",
    )


def _run_response(r: ProjectRun) -> _schemas.ProjectRunResponse:
    return _schemas.ProjectRunResponse(
        id=r.id, module_id=r.module_id,
        module_name=r.module.name if r.module else "",
        user_id=r.user_id, run_type=r.run_type, status=r.status,
        started_at=r.started_at, completed_at=r.completed_at,
    )


async def _sync_modules(session, project: Project, new_modules) -> None:
    """Sync modules from parsed config — add new, keep existing, soft-remove stale."""
    existing = {m.name: m for m in project.modules if m.status != "removed"}
    new_names = {m.name for m in new_modules}

    # Soft-remove modules no longer in config (preserves run history)
    for name, mod in existing.items():
        if name not in new_names:
            mod.status = "removed"
            session.add(mod)

    # Add or update modules
    for m in new_modules:
        if m.name in existing:
            ex = existing[m.name]
            ex.path = m.path
            ex.provider = m.provider
            ex.depends_on = m.depends_on
            session.add(ex)
        else:
            session.add(ProjectModule(
                project_id=project.id,
                name=m.name, path=m.path, provider=m.provider,
                depends_on=m.depends_on,
            ))
