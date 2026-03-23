"""Ollama provider implementation.

Ollama exposes an OpenAI-compatible API, so this delegates to OpenAIProvider
with a custom base_url pointing to the local Ollama server.
Requires `openai` package (same as OpenAI provider).
"""
from __future__ import annotations

import logging

from backend.core import load_kebab_module as _load

logger = logging.getLogger(__name__)

_base = _load("llm/llm-client.py", "llm.llm_client")
_DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"


def _load_openai_provider():
    return _load("llm/openai-provider.py", "llm.openai_provider")


class OllamaProvider(_base.LLMClient):
    """LLMClient implementation backed by a local Ollama server.

    Delegates to OpenAIProvider with Ollama's OpenAI-compatible endpoint.

    Args:
        model: Ollama model name (e.g. 'llama3', 'codellama', 'mistral').
        base_url: Ollama server URL (default: http://localhost:11434/v1).
        api_key: Optional API key (Ollama doesn't require one by default).
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = _DEFAULT_OLLAMA_URL,
        api_key: str = "ollama",
    ) -> None:
        mod = _load_openai_provider()
        self._delegate = mod.OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._delegate.model

    async def complete(self, system, messages, max_tokens=4096):
        try:
            return await self._delegate.complete(system, messages, max_tokens)
        except _base.LLMError as exc:
            # Re-raise with correct provider name instead of "openai"
            raise _base.LLMError(str(exc), provider="ollama", original=exc.original) from exc

    async def stream(self, system, messages, max_tokens=4096):
        try:
            async for delta in self._delegate.stream(system, messages, max_tokens):
                yield delta
        except _base.LLMError as exc:
            raise _base.LLMError(str(exc), provider="ollama", original=exc.original) from exc
