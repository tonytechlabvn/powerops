"""GitHub webhook receiver (Phase 3).

POST /api/webhooks/github — receives and routes GitHub App webhook events.

Security: HMAC-SHA256 signature verification via X-Hub-Signature-256 header.
Idempotency: delivery IDs tracked in webhook_deliveries table.
Processing: returns 200 immediately, dispatches handling via asyncio.create_task().
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request

from backend.core.config import get_settings
from backend.db.database import get_session
from backend.db.models import WebhookDelivery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ---------------------------------------------------------------------------
# Kebab-case core module loader
# ---------------------------------------------------------------------------

def _load_core(filename: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    core_dir = _P(__file__).resolve().parent.parent.parent / "core"
    spec = _ilu.spec_from_file_location(full, core_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _vcs_mgr():
    return _load_core("vcs-run-manager.py", "vcs_run_manager")


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Return True if X-Hub-Signature-256 matches HMAC-SHA256 of body."""
    if not signature_header or not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)


# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------

async def _is_duplicate(delivery_id: str) -> bool:
    """Return True if this delivery ID has already been processed."""
    from sqlalchemy import select
    async with get_session() as session:
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.delivery_id == delivery_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def _record_delivery(delivery_id: str, event_type: str, repo: str) -> None:
    """Persist a delivery record to prevent duplicate processing."""
    async with get_session() as session:
        session.add(WebhookDelivery(
            delivery_id=delivery_id,
            event_type=event_type,
            repo_full_name=repo,
            status="processed",
        ))


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/github")
async def receive_github_webhook(request: Request):
    """Receive GitHub webhook events, verify signature, and dispatch handlers."""
    settings = get_settings()
    body = await request.body()

    # --- Signature verification ---
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(body, sig_header, settings.github_webhook_secret):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    # --- Idempotency guard ---
    if delivery_id and await _is_duplicate(delivery_id):
        logger.info("Duplicate webhook delivery %s — skipping", delivery_id)
        return {"status": "duplicate"}

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    repo = payload.get("repository", {}).get("full_name", "")
    installation_id = payload.get("installation", {}).get("id", 0)

    # Record delivery for idempotency before dispatching
    if delivery_id:
        await _record_delivery(delivery_id, event_type, repo)

    # --- Event routing (fire-and-forget) ---
    mgr = _vcs_mgr()

    if event_type == "pull_request":
        action = payload.get("action", "")
        pr_data = payload.get("pull_request", {})
        asyncio.create_task(
            mgr.handle_pr_event(action, pr_data, repo, installation_id)
        )

    elif event_type == "push":
        ref = payload.get("ref", "")
        commits = payload.get("commits", [])
        asyncio.create_task(
            mgr.handle_push_event(ref, commits, repo, installation_id)
        )

    else:
        logger.debug("Ignoring unhandled GitHub event type: %s", event_type)

    return {"status": "accepted"}
