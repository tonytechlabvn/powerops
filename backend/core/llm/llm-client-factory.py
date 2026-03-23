"""Factory for creating LLM client instances from configuration.

Lazily imports provider modules so unused SDKs are never loaded.
"""
from __future__ import annotations

import logging

from backend.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Valid provider identifiers
SUPPORTED_PROVIDERS = ("anthropic", "openai", "gemini", "ollama")

# Default models per provider
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3",
}


def _load_base():
    from backend.core import load_kebab_module
    return load_kebab_module("llm/llm-client.py", "llm.llm_client")


def create_llm_client(
    provider: str,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
):
    """Create an LLMClient for the given provider.

    Args:
        provider: One of 'anthropic', 'openai', 'gemini', 'ollama'.
        api_key: API key for the provider (not needed for Ollama).
        model: Model identifier. Uses provider default if empty.
        base_url: Custom base URL (only used by Ollama).

    Returns:
        An LLMClient implementation instance.

    Raises:
        LLMError: If the provider is unknown or missing required config.
    """
    from backend.core import load_kebab_module
    base = _load_base()

    resolved_model = model or DEFAULT_MODELS.get(provider, "")

    if provider == "anthropic":
        if not api_key:
            raise base.LLMError("Anthropic API key is required.", provider=provider)
        mod = load_kebab_module("llm/anthropic-provider.py", "llm.anthropic_provider")
        return mod.AnthropicProvider(api_key=api_key, model=resolved_model)

    elif provider == "openai":
        if not api_key:
            raise base.LLMError("OpenAI API key is required.", provider=provider)
        mod = load_kebab_module("llm/openai-provider.py", "llm.openai_provider")
        return mod.OpenAIProvider(api_key=api_key, model=resolved_model)

    elif provider == "gemini":
        if not api_key:
            raise base.LLMError("Gemini API key is required.", provider=provider)
        mod = load_kebab_module("llm/gemini-provider.py", "llm.gemini_provider")
        return mod.GeminiProvider(api_key=api_key, model=resolved_model)

    elif provider == "ollama":
        mod = load_kebab_module("llm/ollama-provider.py", "llm.ollama_provider")
        resolved_url = base_url if base_url else "http://localhost:11434/v1"
        return mod.OllamaProvider(model=resolved_model, base_url=resolved_url, api_key=api_key or "ollama")

    else:
        raise base.LLMError(
            f"Unknown provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
            provider=provider,
        )


def get_llm_client(settings: Settings | None = None):
    """Create an LLMClient from current application settings.

    Reads ai_provider, api keys, and model from Settings to instantiate
    the correct provider. This is the main entry point for AI modules.

    Args:
        settings: Optional Settings instance. Uses cached singleton if None.

    Returns:
        An LLMClient implementation ready for use.
    """
    cfg = settings or get_settings()

    provider = cfg.ai_provider
    model = cfg.ai_model

    # Resolve API key based on active provider
    api_key_map = {
        "anthropic": cfg.anthropic_api_key,
        "openai": cfg.openai_api_key,
        "gemini": cfg.gemini_api_key,
        "ollama": "",
    }
    api_key = api_key_map.get(provider, "")
    base_url = cfg.ollama_base_url if provider == "ollama" else ""

    logger.info("Creating LLM client: provider=%s, model=%s", provider, model)
    return create_llm_client(provider=provider, api_key=api_key, model=model, base_url=base_url)
