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

    # SQLite async connection string (aiosqlite driver)
    db_url: str = "sqlite+aiosqlite:///./terrabot.db"

    # Concurrency cap for simultaneous terraform operations
    max_concurrent_ops: int = 5

    # Per-operation timeout in seconds (default: 30 minutes)
    op_timeout_seconds: int = 1800

    # Anthropic API credentials
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"
    ai_max_tokens: int = 4096

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
