"""OpenAI provider implementation.

Wraps openai.AsyncOpenAI to conform to the LLMClient interface.
Requires `openai` package: pip install openai
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from backend.core import load_kebab_module as _load
_base = _load("llm/llm-client.py", "llm.llm_client")


class OpenAIProvider(_base.LLMClient):
    """LLMClient implementation backed by OpenAI ChatCompletion API.

    Args:
        api_key: OpenAI API key.
        model: Model identifier (e.g. 'gpt-4o', 'gpt-4o-mini').
        base_url: Optional custom base URL (used by Ollama subclass).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "openai package required: pip install openai"
            ) from exc
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**kwargs)
        self._model = model
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def _build_messages(self, system: str, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Prepend system prompt as a system message (OpenAI format)."""
        return [{"role": "system", "content": system}, *messages]

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ):
        base = _base
        import openai
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=self._build_messages(system, messages),
            )
        except openai.APIError as exc:
            raise base.LLMError(str(exc), provider=self.provider_name, original=exc) from exc

        choice = response.choices[0] if response.choices else None
        text = choice.message.content or "" if choice else ""
        usage = base.LLMUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        logger.debug("%s complete: %d in / %d out tokens", self.provider_name, usage.input_tokens, usage.output_tokens)
        return base.LLMResponse(text=text, usage=usage)

    async def stream(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        base = _base
        import openai
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=self._build_messages(system, messages),
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.APIError as exc:
            raise base.LLMError(str(exc), provider=self.provider_name, original=exc) from exc
