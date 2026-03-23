"""AI-powered code assistant wrapping LLMClient with workspace-aware context injection.

Extends LLMClient with editor-specific operations: streaming generation, explanation,
fix suggestion, inline completion, and chat — all with workspace file context.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

from backend.core.llm import LLMError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_MAX_CONTEXT_FILES = 10
_MAX_CONTENT_CHARS = 3000


def _load_prompts():
    """Lazy-load code-assistant-prompt module."""
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/code-assistant-prompt.py", "prompts.code_assistant_prompt")


class AICodeAssistant:
    """LLM-backed code assistant for HCL editing with workspace context.

    Args:
        client: An LLMClient instance.
        max_tokens: Max tokens for completions.
        workspace_dir: Path to the active workspace directory.
    """

    def __init__(self, client, max_tokens: int = 4096, workspace_dir: Path | None = None) -> None:
        self._client = client
        self._max_tokens = max_tokens
        self._workspace_dir = workspace_dir

    async def generate_code(
        self,
        prompt: str,
        current_file: str | None = None,
        current_content: str | None = None,
        provider: str = "aws",
    ) -> AsyncGenerator[str, None]:
        """Stream-generate HCL code from a natural language prompt."""
        p = _load_prompts()
        context = self._build_context(current_file, current_content, provider)
        system = p.get_generate_prompt(provider=provider, context=context)
        async for chunk in self._stream(system, prompt, "generate_code"):
            yield chunk

    async def explain_code(
        self,
        code: str,
        file_path: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a plain-English explanation of the selected HCL block."""
        p = _load_prompts()
        system = p.get_explain_prompt()
        user_msg = f"Explain this HCL block{f' from {file_path}' if file_path else ''}:\n\n```hcl\n{code}\n```"
        async for chunk in self._stream(system, user_msg, "explain_code"):
            yield chunk

    async def suggest_fix(
        self,
        code: str,
        error: str,
        file_path: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a suggested fix for a validation or plan error."""
        p = _load_prompts()
        system = p.get_fix_prompt()
        user_msg = (
            f"Terraform error{f' in {file_path}' if file_path else ''}:\n{error}\n\n"
            f"HCL configuration:\n```hcl\n{code}\n```"
        )
        async for chunk in self._stream(system, user_msg, "suggest_fix"):
            yield chunk

    async def complete_code(
        self,
        code: str,
        cursor_line: int,
        cursor_col: int,
        file_path: str | None = None,
    ) -> str:
        """Return an inline completion suggestion for the cursor position (non-streaming)."""
        p = _load_prompts()
        system = p.get_complete_prompt()
        lines = code.splitlines()
        context_lines = lines[:cursor_line + 1]
        if context_lines and cursor_col < len(context_lines[-1]):
            context_lines[-1] = context_lines[-1][:cursor_col]
        partial = "\n".join(context_lines)
        user_msg = f"Complete this HCL at the cursor:\n```hcl\n{partial}\n```"
        try:
            response = await self._client.complete(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=512,
            )
        except LLMError as exc:
            logger.error("LLM error during complete_code: %s", exc)
            return ""
        return response.text.strip()

    async def chat(
        self,
        messages: list[dict[str, str]],
        current_file: str | None = None,
        current_content: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a conversational response with workspace context."""
        p = _load_prompts()
        context = self._build_context(current_file, current_content)
        system = p.get_chat_prompt(context=context)
        try:
            async for delta in self._client.stream(
                system=system,
                messages=messages,
                max_tokens=self._max_tokens,
            ):
                yield delta
        except LLMError as exc:
            logger.error("LLM error during chat: %s", exc)
            yield f"Error: {exc}"

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _build_context(
        self,
        current_file: str | None,
        current_content: str | None,
        provider: str | None = None,
    ) -> dict:
        """Build context dict with workspace file list, current file info, provider."""
        ctx: dict = {}
        if current_file:
            ctx["current_file"] = current_file
        if provider:
            ctx["provider"] = provider
        if current_content:
            ctx["current_content"] = current_content[:_MAX_CONTENT_CHARS]
        if self._workspace_dir and self._workspace_dir.exists():
            tf_files = [
                f.name for f in self._workspace_dir.glob("*.tf")
            ][:_MAX_CONTEXT_FILES]
            if tf_files:
                ctx["files"] = tf_files
        return ctx

    async def _stream(
        self,
        system: str,
        user_msg: str,
        operation: str,
    ) -> AsyncGenerator[str, None]:
        """Internal streaming helper shared by generate/explain/fix."""
        try:
            async for delta in self._client.stream(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=self._max_tokens,
            ):
                yield delta
        except LLMError as exc:
            logger.error("LLM error during %s: %s", operation, exc)
            yield f"Error: {exc}"
