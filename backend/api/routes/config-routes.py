"""Provider configuration routes.

POST /api/config/provider  — save provider credentials to environment / settings
GET  /api/config/provider  — return current provider config with values redacted
"""
from __future__ import annotations

import os

from fastapi import APIRouter

from backend.api.schemas.request_schemas import ProviderConfigRequest
from backend.api.schemas.response_schemas import OkResponse, ProviderConfigResponse

router = APIRouter(prefix="/api/config", tags=["config"])

# In-memory store for provider config (keys -> masked flag).
# In production this would persist to an encrypted store or secrets manager.
_provider_store: dict[str, dict[str, str]] = {}


@router.post("/provider", response_model=OkResponse)
async def save_provider_config(body: ProviderConfigRequest) -> OkResponse:
    """Store provider credentials. Values are written to process env vars.

    Credentials are also kept in an in-memory registry so GET can show keys.
    This is intentionally simple; replace with Vault/SSM in production.
    """
    _provider_store[body.provider] = {k: "***" for k in body.credentials}
    # Inject into environment so TerraformRunner subprocess inherits them
    for key, value in body.credentials.items():
        os.environ[key] = value
    return OkResponse(message=f"Provider '{body.provider}' configured successfully.")


@router.get("/provider", response_model=ProviderConfigResponse)
async def get_provider_config(provider: str = "aws") -> ProviderConfigResponse:
    """Return current provider config with credential values masked."""
    masked = _provider_store.get(provider, {})
    return ProviderConfigResponse(
        provider=provider,
        configured=bool(masked),
        credentials_redacted=masked,
    )
