"""Google Gemini provider implementation.

Wraps google.genai async client to conform to the LLMClient interface.
Requires `google-genai` package: pip install google-genai
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from backend.core import load_kebab_module as _load
_base = _load("llm/llm-client.py", "llm.llm_client")


class GeminiProvider(_base.LLMClient):
    """LLMClient implementation backed by Google Gemini API.

    Args:
        api_key: Google AI API key.
        model: Model identifier (e.g. 'gemini-2.0-flash', 'gemini-2.5-pro').
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "google-genai package required: pip install google-genai"
            ) from exc
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    def _build_contents(self, system: str, messages: list[dict[str, str]]) -> tuple[str, list[dict]]:
        """Convert common message format to Gemini content format.

        Returns (system_instruction, contents) tuple.
        Gemini uses system_instruction as a separate parameter and
        contents as a list of Content-like dicts.
        """
        contents = []
        for msg in messages:
            # Gemini uses "model" instead of "assistant"
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return system, contents

    async def complete(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ):
        base = _base
        from google import genai
        from google.genai import types

        system_instruction, contents = self._build_contents(system, messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise base.LLMError(str(exc), provider="gemini", original=exc) from exc

        text = response.text or "" if response else ""
        # Gemini usage metadata
        usage = base.LLMUsage()
        if response and response.usage_metadata:
            usage.input_tokens = response.usage_metadata.prompt_token_count or 0
            usage.output_tokens = response.usage_metadata.candidates_token_count or 0
        logger.debug("gemini complete: %d in / %d out tokens", usage.input_tokens, usage.output_tokens)
        return base.LLMResponse(text=text, usage=usage)

    async def stream(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        base = _base
        from google.genai import types

        system_instruction, contents = self._build_contents(system, messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
        )
        try:
            response_stream = await self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config=config,
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            raise base.LLMError(str(exc), provider="gemini", original=exc) from exc
