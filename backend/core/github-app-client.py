"""GitHub App authentication and API client (Phase 3).

Provides: JWT generation, installation token caching, repo cloning,
PR comment upsert (via bot marker), commit status updates, PR metadata fetch.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import jwt  # PyJWT

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
_BOT_MARKER = "<!-- powerops-bot -->"

# In-memory token cache: installation_id -> {"token": str, "expires_at": float}
_token_cache: dict[int, dict[str, Any]] = {}
_cache_lock = asyncio.Lock()


def generate_app_jwt() -> str:
    """Sign a 10-minute App JWT using the configured RS256 private key."""
    settings = get_settings()
    if not settings.github_app_id or not settings.github_private_key:
        raise ValueError("GitHub App credentials not configured")

    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued-at: 60 s in the past to allow clock skew
        "exp": now + (10 * 60),
        "iss": settings.github_app_id,
    }
    private_key = settings.github_private_key.replace("\\n", "\n")
    return jwt.encode(payload, private_key, algorithm="RS256")


# ---------------------------------------------------------------------------
# Installation token (cached)
# ---------------------------------------------------------------------------


async def get_installation_token(installation_id: int) -> str:
    """Return a valid installation access token, refreshing from GitHub if expired."""
    async with _cache_lock:
        cached = _token_cache.get(installation_id)
        # Leave 60-second buffer before actual expiry
        if cached and cached["expires_at"] > time.time() + 60:
            return cached["token"]

        hdrs = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {generate_app_jwt()}"}
        url = f"{_GITHUB_API}/app/installations/{installation_id}/access_tokens"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=hdrs)
            resp.raise_for_status()
            data = resp.json()

        token = data["token"]
        try:
            expires_at = datetime.fromisoformat(
                data.get("expires_at", "").replace("Z", "+00:00")
            ).timestamp()
        except (ValueError, AttributeError):
            expires_at = time.time() + 3600

        _token_cache[installation_id] = {"token": token, "expires_at": expires_at}
        logger.debug("Fetched installation token for installation %s", installation_id)
        return token


# ---------------------------------------------------------------------------
# Repository operations
# ---------------------------------------------------------------------------


def clone_repo(repo_full_name: str, ref: str, target_dir: str, token: str) -> Path:
    """Shallow-clone a GitHub repo at a specific ref using token-auth HTTPS."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, clone_url, str(target)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed for {repo_full_name}@{ref}: {result.stderr}")
    logger.info("Cloned %s@%s into %s", repo_full_name, ref, target)
    return target


async def post_pr_comment(
    repo: str, pr_number: int, body: str, token: str
) -> None:
    """Post a PR comment. Updates existing bot comment if found."""
    marked_body = f"{_BOT_MARKER}\n{body}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient() as client:
        # Search for an existing bot comment to update
        existing_id = await _find_bot_comment(client, repo, pr_number, headers)

        if existing_id:
            url = f"{_GITHUB_API}/repos/{repo}/issues/comments/{existing_id}"
            resp = await client.patch(url, headers=headers, json={"body": marked_body})
        else:
            url = f"{_GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
            resp = await client.post(url, headers=headers, json={"body": marked_body})

        resp.raise_for_status()
        action = "Updated" if existing_id else "Posted"
        logger.info("%s PR comment on %s#%s", action, repo, pr_number)


async def _find_bot_comment(
    client: httpx.AsyncClient, repo: str, pr_number: int, headers: dict
) -> int | None:
    """Return the ID of an existing bot comment, or None."""
    url = f"{_GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    resp = await client.get(url, headers=headers, params={"per_page": 100})
    if resp.status_code != 200:
        return None
    for comment in resp.json():
        if _BOT_MARKER in comment.get("body", ""):
            return comment["id"]
    return None


# ---------------------------------------------------------------------------
# Commit status
# ---------------------------------------------------------------------------


async def update_check_status(
    repo: str,
    sha: str,
    state: str,
    description: str,
    target_url: str,
    token: str,
) -> None:
    """Post a commit status (pending | success | failure | error)."""
    url = f"{_GITHUB_API}/repos/{repo}/statuses/{sha}"
    payload = {
        "state": state,
        "description": description[:140],  # GitHub limit
        "target_url": target_url,
        "context": "powerops/terraform-plan",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
            json=payload,
        )
        resp.raise_for_status()
    logger.debug("Updated commit status %s → %s for %s@%s", repo, state, repo, sha[:8])


async def get_pr_info(repo: str, pr_number: int, token: str) -> dict:
    """Fetch pull request metadata from GitHub."""
    url = f"{_GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
        )
        resp.raise_for_status()
        return resp.json()
