"""Module Registry Manager — CRUD, versioning, and archive storage.

Stores module archives on disk under:
  {working_dir}/registry/{org_id}/{namespace}/{name}/{provider}/{version}.zip
Records metadata in the DB via RegistryModule + RegistryModuleVersion models.
"""
from __future__ import annotations

import importlib.util as _ilu
import io
import json
import logging
import sys as _sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy-load sibling kebab-case module
# ---------------------------------------------------------------------------

def _load_parser():
    alias = "backend.core.module_registry_parser"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(
        alias, Path(__file__).resolve().parent / "module-registry-parser.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ModuleRegistryManager:
    """Handles publish/query/deprecate lifecycle for registry modules."""

    def _registry_root(self) -> Path:
        return get_settings().working_dir / "registry"

    def _archive_path(
        self, org_id: str, namespace: str, name: str, provider: str, version: str
    ) -> Path:
        return (
            self._registry_root() / org_id / namespace / name / provider / f"{version}.zip"
        )

    # ------------------------------------------------------------------
    # Module CRUD
    # ------------------------------------------------------------------

    async def publish_module(
        self,
        session: AsyncSession,
        org_id: str,
        namespace: str,
        name: str,
        provider: str,
        description: str,
        tags: list[str],
        user_id: str,
    ) -> Any:
        """Create a registry module record (no version yet)."""
        from backend.db.models import RegistryModule  # type: ignore[attr-defined]

        existing = (await session.execute(
            select(RegistryModule).where(
                RegistryModule.org_id == org_id,
                RegistryModule.namespace == namespace,
                RegistryModule.name == name,
                RegistryModule.provider == provider,
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(409, "Module already exists; publish a new version instead")

        module = RegistryModule(
            namespace=namespace,
            name=name,
            provider=provider,
            description=description,
            org_id=org_id,
            tags=tags,
            published_by=user_id,
        )
        session.add(module)
        await session.flush()
        return module

    async def list_modules(
        self,
        session: AsyncSession,
        org_id: str,
        search: str | None = None,
        provider: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Any]:
        from backend.db.models import RegistryModule  # type: ignore[attr-defined]

        q = select(RegistryModule).where(
            RegistryModule.org_id == org_id,
            RegistryModule.is_deprecated == False,  # noqa: E712
        )
        if search:
            like = f"%{search}%"
            from sqlalchemy import or_
            q = q.where(or_(
                RegistryModule.name.ilike(like),
                RegistryModule.description.ilike(like),
                RegistryModule.namespace.ilike(like),
            ))
        if provider:
            q = q.where(RegistryModule.provider == provider)
        return list((await session.execute(q.order_by(RegistryModule.created_at.desc()))).scalars())

    async def get_module(self, session: AsyncSession, module_id: str) -> Any:
        from backend.db.models import RegistryModule  # type: ignore[attr-defined]

        module = (await session.execute(
            select(RegistryModule).where(RegistryModule.id == module_id)
        )).scalar_one_or_none()
        if not module:
            raise HTTPException(404, "Module not found")
        return module

    async def deprecate_module(self, session: AsyncSession, module_id: str) -> None:
        module = await self.get_module(session, module_id)
        module.is_deprecated = True
        session.add(module)

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    async def publish_version(
        self,
        session: AsyncSession,
        module_id: str,
        version: str,
        archive_bytes: bytes,
        user_id: str,
    ) -> Any:
        """Store archive on disk, extract docs metadata, record DB row."""
        from backend.db.models import RegistryModule, RegistryModuleVersion  # type: ignore[attr-defined]

        module = await self.get_module(session, module_id)

        # Check duplicate version
        existing_ver = (await session.execute(
            select(RegistryModuleVersion).where(
                RegistryModuleVersion.module_id == module_id,
                RegistryModuleVersion.version == version,
            )
        )).scalar_one_or_none()
        if existing_ver:
            raise HTTPException(409, f"Version {version} already exists")

        # Check version cap
        count = len((await session.execute(
            select(RegistryModuleVersion).where(RegistryModuleVersion.module_id == module_id)
        )).scalars().all())
        if count >= 100:
            raise HTTPException(400, "Maximum 100 versions per module reached")

        parser = _load_parser()
        parser.validate_archive(archive_bytes)

        # Persist archive to disk
        arch_path = self._archive_path(
            module.org_id, module.namespace, module.name, module.provider, version
        )
        arch_path.parent.mkdir(parents=True, exist_ok=True)
        arch_path.write_bytes(archive_bytes)

        # Extract metadata
        checksum = parser.checksum_bytes(archive_bytes)
        readme = parser.extract_readme(arch_path)
        variables = parser.extract_variables(arch_path)
        outputs = parser.extract_outputs(arch_path)
        resources = parser.extract_resources(arch_path)

        ver = RegistryModuleVersion(
            module_id=module_id,
            version=version,
            archive_path=str(arch_path),
            archive_checksum=checksum,
            readme_content=readme,
            variables_json=json.dumps(variables),
            outputs_json=json.dumps(outputs),
            resources_json=json.dumps(resources),
            published_by=user_id,
        )
        session.add(ver)
        await session.flush()
        return ver

    async def list_versions(self, session: AsyncSession, module_id: str) -> list[Any]:
        from backend.db.models import RegistryModuleVersion  # type: ignore[attr-defined]

        await self.get_module(session, module_id)
        return list((await session.execute(
            select(RegistryModuleVersion)
            .where(RegistryModuleVersion.module_id == module_id)
            .order_by(RegistryModuleVersion.published_at.desc())
        )).scalars())

    async def get_version(
        self, session: AsyncSession, module_id: str, version: str
    ) -> Any:
        from backend.db.models import RegistryModuleVersion  # type: ignore[attr-defined]

        ver = (await session.execute(
            select(RegistryModuleVersion).where(
                RegistryModuleVersion.module_id == module_id,
                RegistryModuleVersion.version == version,
            )
        )).scalar_one_or_none()
        if not ver:
            raise HTTPException(404, f"Version {version} not found")
        return ver

    async def get_latest_version(self, session: AsyncSession, module_id: str) -> Any | None:
        from backend.db.models import RegistryModuleVersion  # type: ignore[attr-defined]

        rows = (await session.execute(
            select(RegistryModuleVersion)
            .where(
                RegistryModuleVersion.module_id == module_id,
                RegistryModuleVersion.is_deprecated == False,  # noqa: E712
            )
            .order_by(RegistryModuleVersion.published_at.desc())
        )).scalars().all()
        return rows[0] if rows else None

    async def get_download_path(
        self, session: AsyncSession, module_id: str, version: str
    ) -> Path:
        ver = await self.get_version(session, module_id, version)
        path = Path(ver.archive_path)
        if not path.exists():
            raise HTTPException(404, "Archive file not found on disk")
        return path

    async def deprecate_version(
        self, session: AsyncSession, module_id: str, version: str
    ) -> None:
        ver = await self.get_version(session, module_id, version)
        ver.is_deprecated = True
        session.add(ver)
