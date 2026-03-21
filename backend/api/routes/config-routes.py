"""Provider configuration routes.

POST /api/config/provider  — save provider credentials to environment / settings
GET  /api/config/provider  — return current provider config with values redacted
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter

from backend.api.schemas.request_schemas import ProviderConfigRequest
from backend.api.schemas.response_schemas import OkResponse, ProviderConfigResponse
from backend.core.config import get_settings

router = APIRouter(prefix="/api/config", tags=["config"])
logger = logging.getLogger(__name__)

# Map frontend form keys to the env vars Terraform actually reads
_ENV_VAR_MAP: dict[str, str] = {
    "aws_access_key_id": "AWS_ACCESS_KEY_ID",
    "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
    "aws_region": "AWS_DEFAULT_REGION",
    "proxmox_api_url": "PM_API_URL",
    "proxmox_user": "PM_USER",
    "proxmox_password": "PM_PASS",
    "proxmox_tls_insecure": "PM_TLS_INSECURE",
}


def _config_file() -> Path:
    """Persistent config file path (inside the Docker data volume)."""
    data_dir = Path(get_settings().db_url.replace("sqlite+aiosqlite:///", "")).parent
    return data_dir / "provider-config.json"


def _load_store() -> dict[str, dict[str, str]]:
    """Load persisted provider credentials from disk."""
    path = _config_file()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load config file: %s", exc)
    return {}


def _save_store(store: dict[str, dict[str, str]]) -> None:
    """Persist provider credentials to disk."""
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _inject_env(credentials: dict[str, str]) -> None:
    """Set env vars from credentials, mapping lowercase keys to uppercase."""
    for key, value in credentials.items():
        env_key = _ENV_VAR_MAP.get(key, key.upper())
        os.environ[env_key] = value


def load_persisted_config() -> None:
    """Called on app startup to restore saved credentials into env vars."""
    store = _load_store()
    for provider, creds in store.items():
        _inject_env(creds)
        logger.info("Loaded %s config (%d keys)", provider, len(creds))


@router.post("/provider", response_model=OkResponse)
async def save_provider_config(body: ProviderConfigRequest) -> OkResponse:
    """Store provider credentials. Persisted to disk and injected into env."""
    store = _load_store()
    store[body.provider] = body.credentials
    _save_store(store)
    _inject_env(body.credentials)
    return OkResponse(message=f"Provider '{body.provider}' configured successfully.")


@router.get("/provider", response_model=ProviderConfigResponse)
async def get_provider_config(provider: str = "aws") -> ProviderConfigResponse:
    """Return current provider config with credential values masked."""
    store = _load_store()
    creds = store.get(provider, {})
    masked = {k: "***" for k in creds}
    return ProviderConfigResponse(
        provider=provider,
        configured=bool(masked),
        credentials_redacted=masked,
    )
