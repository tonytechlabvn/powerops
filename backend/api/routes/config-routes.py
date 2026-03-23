"""Provider and AI configuration routes.

POST /api/config/provider  — save provider credentials to environment / settings
GET  /api/config/provider  — return current provider config with values redacted
POST /api/config/ai        — save AI LLM provider configuration
GET  /api/config/ai        — return current AI config (keys masked)
GET  /api/config/ai/providers — list available AI providers with status
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter

from pydantic import BaseModel

from backend.api.schemas.request_schemas import ProviderConfigRequest
from backend.api.schemas.response_schemas import OkResponse, ProviderConfigResponse
from backend.core.config import get_settings
from backend.core.llm import SUPPORTED_PROVIDERS, DEFAULT_MODELS

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


# ---------------------------------------------------------------------------
# AI / LLM provider configuration
# ---------------------------------------------------------------------------

class AIConfigRequest(BaseModel):
    """Request body for saving AI provider configuration."""
    provider: str  # anthropic | openai | gemini | ollama
    api_key: str = ""
    model: str = ""
    max_tokens: int = 4096
    base_url: str = ""  # only for ollama


class AIProviderStatus(BaseModel):
    """Status of a single AI provider."""
    name: str
    configured: bool
    default_model: str


class AIConfigResponse(BaseModel):
    """Current AI configuration (keys masked)."""
    provider: str
    model: str
    max_tokens: int
    api_key_set: bool
    base_url: str = ""


def _ai_config_file() -> Path:
    """Persistent AI config file path (alongside provider-config.json)."""
    return _config_file().parent / "ai-config.json"


def _load_ai_config() -> dict:
    """Load persisted AI configuration from disk."""
    path = _ai_config_file()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load AI config: %s", exc)
    return {}


def _save_ai_config(config: dict) -> None:
    """Persist AI configuration to disk."""
    path = _ai_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def load_persisted_ai_config() -> None:
    """Called on app startup to apply saved AI config into environment.

    Sets TERRABOT_ prefixed env vars so Settings picks them up.
    """
    config = _load_ai_config()
    if not config:
        return

    env_map = {
        "provider": "TERRABOT_AI_PROVIDER",
        "model": "TERRABOT_AI_MODEL",
        "max_tokens": "TERRABOT_AI_MAX_TOKENS",
        "anthropic_api_key": "TERRABOT_ANTHROPIC_API_KEY",
        "openai_api_key": "TERRABOT_OPENAI_API_KEY",
        "gemini_api_key": "TERRABOT_GEMINI_API_KEY",
        "ollama_base_url": "TERRABOT_OLLAMA_BASE_URL",
    }
    for key, env_var in env_map.items():
        if key in config and config[key]:
            os.environ[env_var] = str(config[key])
    logger.info("Loaded AI config: provider=%s, model=%s", config.get("provider", "?"), config.get("model", "?"))


@router.post("/ai", response_model=OkResponse)
async def save_ai_config(body: AIConfigRequest) -> OkResponse:
    """Save AI LLM provider configuration. Persisted to disk and applied."""
    from fastapi import HTTPException
    if body.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{body.provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    config = _load_ai_config()
    old_provider = config.get("provider", "anthropic")
    config["provider"] = body.provider
    # If provider changed and no explicit model given, use provider's default
    if body.model:
        config["model"] = body.model
    elif body.provider != old_provider:
        config["model"] = DEFAULT_MODELS.get(body.provider, "")
    config["max_tokens"] = body.max_tokens

    # Store API key under provider-specific key
    key_field = f"{body.provider}_api_key"
    if body.api_key:
        config[key_field] = body.api_key
    if body.base_url and body.provider == "ollama":
        config["ollama_base_url"] = body.base_url

    _save_ai_config(config)

    # Apply to current environment so Settings picks up changes
    os.environ["TERRABOT_AI_PROVIDER"] = body.provider
    if body.model:
        os.environ["TERRABOT_AI_MODEL"] = body.model
    os.environ["TERRABOT_AI_MAX_TOKENS"] = str(body.max_tokens)
    if body.api_key:
        env_key = f"TERRABOT_{body.provider.upper()}_API_KEY"
        os.environ[env_key] = body.api_key
    if body.base_url and body.provider == "ollama":
        os.environ["TERRABOT_OLLAMA_BASE_URL"] = body.base_url

    # Clear cached Settings so next call picks up new env vars
    get_settings.cache_clear()

    return OkResponse(message=f"AI provider '{body.provider}' configured successfully.")


@router.get("/ai", response_model=AIConfigResponse)
async def get_ai_config() -> AIConfigResponse:
    """Return current AI configuration with API key masked."""
    cfg = get_settings()
    # Check if active provider has an API key set
    key_map = {
        "anthropic": cfg.anthropic_api_key,
        "openai": cfg.openai_api_key,
        "gemini": cfg.gemini_api_key,
        "ollama": "",  # no key needed
    }
    api_key_set = bool(key_map.get(cfg.ai_provider, ""))
    return AIConfigResponse(
        provider=cfg.ai_provider,
        model=cfg.ai_model,
        max_tokens=cfg.ai_max_tokens,
        api_key_set=api_key_set or cfg.ai_provider == "ollama",
        base_url=cfg.ollama_base_url if cfg.ai_provider == "ollama" else "",
    )


@router.get("/ai/providers")
async def list_ai_providers() -> list[AIProviderStatus]:
    """Return list of available AI providers with configuration status."""
    cfg = get_settings()
    key_map = {
        "anthropic": bool(cfg.anthropic_api_key),
        "openai": bool(cfg.openai_api_key),
        "gemini": bool(cfg.gemini_api_key),
        "ollama": True,  # always "configured" (local, no key needed)
    }
    return [
        AIProviderStatus(
            name=p,
            configured=key_map.get(p, False),
            default_model=DEFAULT_MODELS.get(p, ""),
        )
        for p in SUPPORTED_PROVIDERS
    ]
