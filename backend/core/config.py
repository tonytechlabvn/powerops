"""Application configuration via Pydantic BaseSettings.

All settings can be overridden with TERRABOT_ prefixed environment variables.
Example: TERRABOT_TERRAFORM_BINARY=/usr/local/bin/terraform
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Terraform binary path — override if not on PATH
    terraform_binary: str = "terraform"

    # Base directory for per-job workspace isolation
    working_dir: Path = Path("./workspaces")

    # Root directory for Jinja2 blueprint templates
    template_dir: Path = Path("./templates")

    # Database connection string (PostgreSQL default, SQLite fallback)
    db_url: str = "postgresql+asyncpg://powerops:powerops@postgres:5432/powerops"

    # Concurrency cap for simultaneous terraform operations
    max_concurrent_ops: int = 5

    # Per-operation timeout in seconds (default: 30 minutes)
    op_timeout_seconds: int = 1800

    # --- AI / LLM provider ---
    # Active provider: anthropic | openai | gemini | ollama
    ai_provider: str = "anthropic"
    ai_model: str = "claude-sonnet-4-20250514"
    ai_max_tokens: int = 4096
    # Per-provider API keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    # Ollama local server URL with OpenAI-compatible /v1 path
    ollama_base_url: str = "http://localhost:11434/v1"

    # --- Phase 1: State management ---
    # Base64-encoded 32-byte key for AES-256-GCM state encryption.
    # If empty, state stored unencrypted (dev mode) with warning.
    state_encryption_key: str = ""
    # Max state versions to keep per workspace before pruning
    state_max_versions: int = 50
    # State lock lease timeout in seconds (default 10 min)
    state_lock_timeout_seconds: int = 600

    # --- Phase 2: Auth & RBAC ---
    # Legacy JWT secret (kept for API token signing; Keycloak uses RS256 JWKS)
    jwt_secret: str = ""
    # JWT access token TTL in minutes (Keycloak controls actual token lifespan)
    jwt_access_ttl_minutes: int = 15
    # JWT refresh token TTL in days
    jwt_refresh_ttl_days: int = 7

    # --- Keycloak OIDC ---
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "powerops"
    keycloak_client_id: str = "powerops-api"
    keycloak_client_secret: str = ""
    # Public-facing Keycloak URL (for browser redirects; defaults to keycloak_url)
    keycloak_public_url: str = ""

    # --- Phase 3: VCS / GitHub App ---
    # GitHub App ID (set after manifest flow or manual creation)
    github_app_id: int = 0
    # GitHub App private key PEM content (stored in DB after manifest flow)
    github_private_key: str = ""
    # GitHub webhook secret for HMAC-SHA256 verification
    github_webhook_secret: str = ""
    # Max concurrent VCS-triggered runs
    vcs_max_concurrent_runs: int = 10

    # --- Phase 4: Policy (OPA) ---
    # OPA sidecar URL
    opa_url: str = "http://opa:8181"

    # --- HCP Terraform Cloud ---
    tfc_api_token: str = ""
    tfc_base_url: str = "https://app.terraform.io"
    # Enable/disable policy checks on runs
    policy_check_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="TERRABOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
