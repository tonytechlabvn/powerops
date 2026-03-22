"""Private Module Registry API routes.

Management API:
  POST   /api/registry/modules                   — publish new module
  GET    /api/registry/modules                   — search/list modules
  GET    /api/registry/modules/{id}              — module detail
  PATCH  /api/registry/modules/{id}              — update metadata
  DELETE /api/registry/modules/{id}              — deprecate module
  POST   /api/registry/modules/{id}/versions     — publish new version (multipart)
  GET    /api/registry/modules/{id}/versions     — list versions
  GET    /api/registry/modules/{id}/versions/{v} — version detail
  GET    /api/registry/modules/{id}/docs         — auto-generated documentation

Terraform Registry Protocol v1 (for terraform init):
  GET  /api/registry/v1/modules/{ns}/{name}/{provider}/versions
  GET  /api/registry/v1/modules/{ns}/{name}/{provider}/{version}/download
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import select

from backend.db.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/registry/modules", tags=["module-registry"])
v1_router = APIRouter(prefix="/api/registry/v1/modules", tags=["terraform-registry-protocol"])


# ---------------------------------------------------------------------------
# Lazy loaders
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
    return _load("schemas/registry-schemas.py", "api.schemas.registry_schemas")


def _manager():
    full = "backend.core.module_registry_manager"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent.parent / "core" / "module-registry-manager.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _docs_generator():
    full = "backend.core.module_docs_generator"
    if full in _sys.modules:
        return _sys.modules[full]
    spec = _ilu.spec_from_file_location(
        full, _P(__file__).resolve().parent.parent.parent / "core" / "module-docs-generator.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(401, "Not authenticated")
    return user


# ---------------------------------------------------------------------------
# Management API — Modules
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def publish_module(request: Request):
    """Publish a new module (no version yet)."""
    user = _require_auth(request)
    body = _schemas().PublishModuleRequest(**(await request.json()))
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        module = await mgr.publish_module(
            session,
            org_id=user.get("org_id", ""),
            namespace=body.namespace,
            name=body.name,
            provider=body.provider,
            description=body.description,
            tags=body.tags,
            user_id=user["user_id"],
        )
        return _module_response(module, mgr, session)


@router.get("")
async def list_modules(
    request: Request,
    search: str | None = None,
    provider: str | None = None,
):
    """List/search modules for the current org."""
    user = _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        modules = await mgr.list_modules(
            session, org_id=user.get("org_id", ""), search=search, provider=provider
        )
        return [_module_summary(m) for m in modules]


@router.get("/{module_id}")
async def get_module(module_id: str, request: Request):
    """Get module details including all versions."""
    _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        module = await mgr.get_module(session, module_id)
        versions = await mgr.list_versions(session, module_id)
        latest = await mgr.get_latest_version(session, module_id)
        return {
            **_module_summary(module),
            "latest_version": latest.version if latest else None,
            "versions": [_version_summary(v) for v in versions],
        }


@router.patch("/{module_id}")
async def update_module(module_id: str, request: Request):
    """Update module metadata (description, tags)."""
    user = _require_auth(request)
    body = _schemas().UpdateModuleRequest(**(await request.json()))
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        module = await mgr.get_module(session, module_id)
        if body.description is not None:
            module.description = body.description
        if body.tags is not None:
            module.tags = body.tags
        session.add(module)
        return _module_summary(module)


@router.delete("/{module_id}", status_code=204)
async def deprecate_module(module_id: str, request: Request):
    """Soft-delete a module (sets is_deprecated=True)."""
    _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        await mgr.deprecate_module(session, module_id)


# ---------------------------------------------------------------------------
# Management API — Versions
# ---------------------------------------------------------------------------

@router.post("/{module_id}/versions", status_code=201)
async def publish_version(
    module_id: str,
    request: Request,
    version: str,
    archive: UploadFile = File(...),
):
    """Publish a new version via multipart archive upload."""
    user = _require_auth(request)
    archive_bytes = await archive.read()
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        ver = await mgr.publish_version(
            session, module_id=module_id, version=version,
            archive_bytes=archive_bytes, user_id=user["user_id"],
        )
        return _version_detail(ver)


@router.get("/{module_id}/versions")
async def list_versions(module_id: str, request: Request):
    _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        versions = await mgr.list_versions(session, module_id)
        return [_version_summary(v) for v in versions]


@router.get("/{module_id}/versions/{version}")
async def get_version(module_id: str, version: str, request: Request):
    _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        ver = await mgr.get_version(session, module_id, version)
        return _version_detail(ver)


@router.get("/{module_id}/versions/{version}/download")
async def download_version(module_id: str, version: str, request: Request):
    """Download the zip archive for a specific version."""
    _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        path = await mgr.get_download_path(session, module_id, version)
    return FileResponse(
        str(path),
        media_type="application/zip",
        filename=path.name,
    )


@router.get("/{module_id}/docs")
async def get_module_docs(module_id: str, request: Request, version: str | None = None):
    """Return auto-generated documentation for a module version."""
    _require_auth(request)
    mgr = _manager().ModuleRegistryManager()
    async with get_session() as session:
        if version:
            ver = await mgr.get_version(session, module_id, version)
        else:
            ver = await mgr.get_latest_version(session, module_id)
            if not ver:
                raise HTTPException(404, "No versions published yet")
        return {
            "readme": ver.readme_content,
            "variables": json.loads(ver.variables_json or "[]"),
            "outputs": json.loads(ver.outputs_json or "[]"),
            "resources": json.loads(ver.resources_json or "[]"),
        }


# ---------------------------------------------------------------------------
# Terraform Registry Protocol v1
# ---------------------------------------------------------------------------

@v1_router.get("/{namespace}/{name}/{provider}/versions")
async def tf_list_versions(namespace: str, name: str, provider: str, request: Request):
    """Terraform Registry Protocol: version list for terraform init."""
    _require_auth(request)
    from backend.db.models import RegistryModule, RegistryModuleVersion  # type: ignore[attr-defined]

    async with get_session() as session:
        module = (await session.execute(
            select(RegistryModule).where(
                RegistryModule.namespace == namespace,
                RegistryModule.name == name,
                RegistryModule.provider == provider,
                RegistryModule.is_deprecated == False,  # noqa: E712
            )
        )).scalar_one_or_none()
        if not module:
            raise HTTPException(404, "Module not found")

        versions = (await session.execute(
            select(RegistryModuleVersion)
            .where(
                RegistryModuleVersion.module_id == module.id,
                RegistryModuleVersion.is_deprecated == False,  # noqa: E712
            )
            .order_by(RegistryModuleVersion.published_at.desc())
        )).scalars().all()

        return {
            "modules": [{
                "versions": [
                    {"version": v.version, "protocols": ["4.0", "5.1"], "platforms": []}
                    for v in versions
                ]
            }]
        }


@v1_router.get("/{namespace}/{name}/{provider}/{version}/download")
async def tf_download_version(
    namespace: str, name: str, provider: str, version: str, request: Request
):
    """Terraform Registry Protocol: return X-Terraform-Get download URL."""
    _require_auth(request)
    from backend.db.models import RegistryModule, RegistryModuleVersion  # type: ignore[attr-defined]

    async with get_session() as session:
        module = (await session.execute(
            select(RegistryModule).where(
                RegistryModule.namespace == namespace,
                RegistryModule.name == name,
                RegistryModule.provider == provider,
            )
        )).scalar_one_or_none()
        if not module:
            raise HTTPException(404, "Module not found")

        ver = (await session.execute(
            select(RegistryModuleVersion).where(
                RegistryModuleVersion.module_id == module.id,
                RegistryModuleVersion.version == version,
            )
        )).scalar_one_or_none()
        if not ver:
            raise HTTPException(404, f"Version {version} not found")

    from fastapi.responses import Response
    download_url = (
        f"/api/registry/modules/{module.id}/versions/{version}/download"
    )
    return Response(
        status_code=204,
        headers={"X-Terraform-Get": download_url},
    )


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _module_summary(m) -> dict:
    return {
        "id": m.id,
        "namespace": m.namespace,
        "name": m.name,
        "provider": m.provider,
        "description": m.description,
        "org_id": m.org_id,
        "tags": m.tags or [],
        "is_deprecated": m.is_deprecated,
        "published_by": m.published_by,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }


def _module_response(m, mgr, session) -> dict:
    return _module_summary(m)


def _version_summary(v) -> dict:
    return {
        "id": v.id,
        "module_id": v.module_id,
        "version": v.version,
        "archive_checksum": v.archive_checksum,
        "is_deprecated": v.is_deprecated,
        "published_by": v.published_by,
        "published_at": v.published_at.isoformat(),
    }


def _version_detail(v) -> dict:
    return {
        **_version_summary(v),
        "readme_content": v.readme_content,
        "variables": json.loads(v.variables_json or "[]"),
        "outputs": json.loads(v.outputs_json or "[]"),
        "resources": json.loads(v.resources_json or "[]"),
    }
