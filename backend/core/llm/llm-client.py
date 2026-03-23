"""Abstract base class for LLM providers and shared data types.

All provider implementations (Anthropic, OpenAI, Gemini, Ollama) implement
this interface so AI modules can work with any backend transparently.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


class LLMError(Exception):
    """Unified error raised by all LLM providers.

    Wraps provider-specific exceptions (anthropic.APIError, openai.APIError, etc.)
    so callers only need to catch one type.
    """

    def __init__(self, message: str, provider: str = "", original: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.original = original


@dataclass
class LLMUsage:
    """Normalized token usage across providers."""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    """Normalized non-streaming response from any LLM provider."""
    text: str = ""
    usage: LLMUsage = field(default_factory=LLMUsage)


class LLMClient(ABC):
    """Provider-agnostic async LLM client interface.

    All AI modules depend on this interface rather than a specific SDK.
    Implementations handle message format translation, streaming parsing,
    and error wrapping internally.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g. 'anthropic', 'openai')."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model name being used."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a non-streaming chat completion request.

        Args:
            system: System prompt text.
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse with full text and token usage.

        Raises:
            LLMError: On any provider API failure.
        """

    @abstractmethod
    async def stream(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding text deltas.

        Args:
            system: System prompt text.
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
            max_tokens: Maximum tokens in the response.

        Yields:
            Text delta strings as they arrive from the provider.

        Raises:
            LLMError: On any provider API failure.
        """
        # Make this a generator (yield needed for ABC async generators)
        yield ""  # pragma: no cover
