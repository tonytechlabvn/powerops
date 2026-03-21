"""State CRUD, locking, and versioning for Terraform remote state backend.

All database operations use async SQLAlchemy sessions from get_session().
Encryption is delegated to state-encryption.py (loaded via importlib).
"""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, desc, select

from backend.db.database import get_session
from backend.db.models import StateLock, StateVersion, Workspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Kebab-case module loader for state-encryption.py
# ---------------------------------------------------------------------------

def _load_encryption():
    alias = "backend.core.state_encryption"
    if alias in sys.modules:
        return sys.modules[alias]
    mod_path = Path(__file__).parent / "state-encryption.py"
    spec = importlib.util.spec_from_file_location(alias, mod_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _enc():
    return _load_encryption()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_workspace_by_name(session, name: str) -> Workspace | None:
    result = await session.execute(select(Workspace).where(Workspace.name == name))
    return result.scalar_one_or_none()


async def _get_workspace_by_id(session, workspace_id: str) -> Workspace | None:
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    return result.scalar_one_or_none()


def _maybe_encrypt(plaintext: bytes, enc_mod) -> bytes:
    key = enc_mod.load_encryption_key()
    if key is None:
        return plaintext
    return enc_mod.encrypt_state(plaintext, key)


def _maybe_decrypt(data: bytes, enc_mod) -> bytes:
    key = enc_mod.load_encryption_key()
    if key is None:
        return data
    return enc_mod.decrypt_state(data, key)


# ---------------------------------------------------------------------------
# Lock operations
# ---------------------------------------------------------------------------

async def get_lock(workspace_id: str) -> dict | None:
    """Return current lock info dict, or None if unlocked."""
    async with get_session() as session:
        result = await session.execute(
            select(StateLock).where(StateLock.workspace_id == workspace_id)
        )
        lock = result.scalar_one_or_none()
        if lock is None:
            return None
        return {
            "ID": lock.lock_id,
            "Operation": lock.operation,
            "Info": lock.info,
            "Who": lock.holder,
            "Created": lock.created_at.isoformat(),
            "Expires": lock.expires_at.isoformat(),
        }


async def acquire_lock(workspace_id: str, lock_info_json: dict) -> dict:
    """Acquire workspace lock. Returns lock dict on success, raises 423 if locked.

    Auto-releases expired locks before attempting acquisition.
    """
    from backend.core.config import get_settings

    settings = get_settings()
    timeout = settings.state_lock_timeout_seconds

    async with get_session() as session:
        result = await session.execute(
            select(StateLock).where(StateLock.workspace_id == workspace_id)
        )
        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing is not None:
            if existing.expires_at <= now:
                # Expired lock — auto-release
                logger.info(
                    "Auto-releasing expired lock for workspace %s (held by %s)",
                    workspace_id, existing.holder,
                )
                await session.delete(existing)
                await session.flush()
                existing = None
            else:
                # Active lock — return 423
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=423,
                    detail={
                        "ID": existing.lock_id,
                        "Operation": existing.operation,
                        "Info": existing.info,
                        "Who": existing.holder,
                        "Created": existing.created_at.isoformat(),
                    },
                )

        lock_id = lock_info_json.get("ID") or str(uuid.uuid4())
        expires_at = now + timedelta(seconds=timeout)

        new_lock = StateLock(
            workspace_id=workspace_id,
            lock_id=lock_id,
            holder=lock_info_json.get("Who", "unknown"),
            operation=lock_info_json.get("Operation", ""),
            info=lock_info_json.get("Info", ""),
            created_at=now,
            expires_at=expires_at,
        )
        session.add(new_lock)
        logger.info("Lock acquired for workspace %s by %s", workspace_id, new_lock.holder)

        return {
            "ID": lock_id,
            "Operation": new_lock.operation,
            "Info": new_lock.info,
            "Who": new_lock.holder,
            "Created": now.isoformat(),
            "Path": lock_info_json.get("Path", ""),
        }


async def release_lock(workspace_id: str, lock_id: str) -> bool:
    """Release lock if lock_id matches. Returns True on success."""
    async with get_session() as session:
        result = await session.execute(
            select(StateLock).where(StateLock.workspace_id == workspace_id)
        )
        lock = result.scalar_one_or_none()
        if lock is None:
            return False
        if lock.lock_id != lock_id:
            logger.warning(
                "Release attempt with wrong lock_id for workspace %s", workspace_id
            )
            return False
        await session.delete(lock)
        logger.info("Lock released for workspace %s", workspace_id)
        return True


async def force_unlock(workspace_id: str) -> bool:
    """Remove any lock for workspace regardless of lock_id."""
    async with get_session() as session:
        result = await session.execute(
            select(StateLock).where(StateLock.workspace_id == workspace_id)
        )
        lock = result.scalar_one_or_none()
        if lock is None:
            return False
        await session.delete(lock)
        logger.info("Force-unlocked workspace %s", workspace_id)
        return True


# ---------------------------------------------------------------------------
# State read/write operations
# ---------------------------------------------------------------------------

async def push_state(
    workspace_id: str,
    state_bytes: bytes,
    lock_id: str | None = None,
    user: str = "system",
) -> StateVersion:
    """Persist a new state version. Verifies lock_id if provided."""
    enc = _enc()

    # Parse state JSON for metadata
    try:
        state_json = json.loads(state_bytes)
    except Exception:
        state_json = {}

    metadata = enc.extract_state_metadata(state_json)
    checksum = enc.compute_checksum(state_bytes)
    serial = state_json.get("serial", 0)
    lineage = state_json.get("lineage", "")

    encrypted_data = _maybe_encrypt(state_bytes, enc)

    async with get_session() as session:
        # Verify lock if provided
        if lock_id:
            lock_result = await session.execute(
                select(StateLock).where(StateLock.workspace_id == workspace_id)
            )
            lock = lock_result.scalar_one_or_none()
            if lock and lock.lock_id != lock_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=409, detail="Lock ID mismatch.")

        version = StateVersion(
            workspace_id=workspace_id,
            serial=serial,
            lineage=lineage,
            state_data=encrypted_data,
            metadata_json=json.dumps(metadata),
            checksum=checksum,
            created_by=user,
        )
        session.add(version)
        logger.info(
            "State pushed for workspace %s serial=%s by %s", workspace_id, serial, user
        )

    # Prune old versions asynchronously (best-effort)
    try:
        await prune_versions(workspace_id)
    except Exception as exc:
        logger.warning("Version pruning failed for %s: %s", workspace_id, exc)

    return version


async def pull_state(workspace_id: str) -> bytes | None:
    """Return latest decrypted state bytes, or None if no state exists."""
    enc = _enc()
    async with get_session() as session:
        result = await session.execute(
            select(StateVersion)
            .where(StateVersion.workspace_id == workspace_id)
            .order_by(desc(StateVersion.serial))
            .limit(1)
        )
        version = result.scalar_one_or_none()
        if version is None:
            return None
        return _maybe_decrypt(version.state_data, enc)


async def pull_state_version(workspace_id: str, serial: int) -> bytes | None:
    """Return decrypted state bytes for a specific serial, or None."""
    enc = _enc()
    async with get_session() as session:
        result = await session.execute(
            select(StateVersion).where(
                StateVersion.workspace_id == workspace_id,
                StateVersion.serial == serial,
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            return None
        return _maybe_decrypt(version.state_data, enc)


async def list_versions(
    workspace_id: str, limit: int = 20, offset: int = 0
) -> list[dict]:
    """Return paginated version list (newest first), metadata only."""
    async with get_session() as session:
        result = await session.execute(
            select(StateVersion)
            .where(StateVersion.workspace_id == workspace_id)
            .order_by(desc(StateVersion.serial))
            .limit(limit)
            .offset(offset)
        )
        versions = result.scalars().all()
        out = []
        for v in versions:
            meta = json.loads(v.metadata_json) if v.metadata_json else {}
            out.append({
                "id": v.id,
                "serial": v.serial,
                "lineage": v.lineage,
                "checksum": v.checksum,
                "resource_count": meta.get("resource_count", 0),
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by,
            })
        return out


async def rollback_state(
    workspace_id: str, serial: int, user: str = "system"
) -> StateVersion:
    """Rollback to a previous serial by re-pushing that version's data."""
    state_bytes = await pull_state_version(workspace_id, serial)
    if state_bytes is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404, detail=f"State serial {serial} not found."
        )

    # Re-parse and bump serial to make rollback the newest version
    try:
        state_json = json.loads(state_bytes)
        # Get current max serial and increment by 1
        async with get_session() as session:
            result = await session.execute(
                select(StateVersion)
                .where(StateVersion.workspace_id == workspace_id)
                .order_by(desc(StateVersion.serial))
                .limit(1)
            )
            latest = result.scalar_one_or_none()
            next_serial = (latest.serial + 1) if latest else serial
        state_json["serial"] = next_serial
        state_bytes = json.dumps(state_json).encode()
    except Exception:
        pass

    version = await push_state(workspace_id, state_bytes, user=user)
    logger.info(
        "Rollback to serial %s completed for workspace %s by %s",
        serial, workspace_id, user,
    )
    return version


async def get_outputs(workspace_id: str) -> dict:
    """Return non-sensitive outputs from the latest state."""
    state_bytes = await pull_state(workspace_id)
    if state_bytes is None:
        return {}
    try:
        state_json = json.loads(state_bytes)
        raw_outputs: dict = state_json.get("outputs", {})
        result = {}
        for name, meta in raw_outputs.items():
            if not meta.get("sensitive", False):
                result[name] = meta.get("value")
            else:
                result[name] = "<sensitive>"
        return result
    except Exception as exc:
        logger.warning("Failed to parse outputs for workspace %s: %s", workspace_id, exc)
        return {}


async def prune_versions(workspace_id: str) -> int:
    """Delete old versions beyond state_max_versions. Returns count deleted."""
    from backend.core.config import get_settings
    max_versions = get_settings().state_max_versions

    async with get_session() as session:
        result = await session.execute(
            select(StateVersion.id)
            .where(StateVersion.workspace_id == workspace_id)
            .order_by(desc(StateVersion.serial))
            .offset(max_versions)
        )
        old_ids = [row[0] for row in result.fetchall()]
        if not old_ids:
            return 0
        await session.execute(
            delete(StateVersion).where(StateVersion.id.in_(old_ids))
        )
        logger.info(
            "Pruned %d old state versions for workspace %s", len(old_ids), workspace_id
        )
        return len(old_ids)
