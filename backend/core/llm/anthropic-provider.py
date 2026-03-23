"""Anthropic Claude provider implementation.

Wraps anthropic.AsyncAnthropic to conform to the LLMClient interface.
This is the default provider — already a project dependency.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Load base classes at module level for ABC inheritance
from backend.core import load_kebab_module as _load
_base = _load("llm/llm-client.py", "llm.llm_client")


class AnthropicProvider(_base.LLMClient):
    """LLMClient implementation backed by Anthropic Claude API.

    Args:
        api_key: Anthropic API key.
        model: Model identifier (e.g. 'claude-sonnet-4-20250514').
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ):
        """Non-streaming completion via Anthropic messages API."""
        base = _base
        import anthropic
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
        except anthropic.APIError as exc:
            raise base.LLMError(str(exc), provider="anthropic", original=exc) from exc

        text = response.content[0].text if response.content else ""
        usage = base.LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        logger.debug("anthropic complete: %d in / %d out tokens", usage.input_tokens, usage.output_tokens)
        return base.LLMResponse(text=text, usage=usage)

    async def stream(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Streaming completion via Anthropic messages API."""
        base = _base
        import anthropic
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            ) as stream:
                async for delta in stream.text_stream:
                    yield delta
                final = await stream.get_final_message()
                logger.debug(
                    "anthropic stream: %d in / %d out tokens",
                    final.usage.input_tokens,
                    final.usage.output_tokens,
                )
        except anthropic.APIError as exc:
            raise base.LLMError(str(exc), provider="anthropic", original=exc) from exc
