"""Main AI agent for HCL generation, explanation, diagnosis, and chat.

Uses the LLM provider abstraction layer for provider-agnostic AI calls.
All prompt logic lives in core/prompts/. Parsing helpers in ai-agent-helpers.py.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from backend.core.llm import LLMError
from backend.core.models import DiagnosisResult, GenerationResult, ReviewResult
from backend.core.prompts import (
    chat_prompt,
    diagnose_prompt,
    explain_prompt,
    generate_prompt,
    review_prompt,
)

logger = logging.getLogger(__name__)


def _helpers():
    """Lazy-load ai-agent-helpers via the core importlib bridge (kebab filename)."""
    from backend.core import load_kebab_module
    return load_kebab_module("ai-agent-helpers.py", "ai_agent_helpers")


class AIAgent:
    """LLM-backed AI agent for all TerraBot intelligence features.

    Args:
        client: An LLMClient instance (from get_llm_client or create_llm_client).
        max_tokens: Max tokens for completions (default 4096).
    """

    def __init__(self, client, max_tokens: int = 4096) -> None:
        self._client = client
        self._max_tokens = max_tokens

    async def generate_hcl(
        self,
        request: str,
        provider: str = "aws",
        context: dict[str, Any] | None = None,
    ) -> GenerationResult:
        """Generate Terraform HCL from a natural-language request.

        Runs up to 2 retries if the response fails HCL validation.
        """
        from backend.core import hcl_validator
        h = _helpers()

        system = generate_prompt.get_prompt(provider=provider)
        user_parts = [request]
        if context:
            user_parts.append(f"\nAdditional context:\n{json.dumps(context, indent=2)}")
        user_msg = "\n".join(user_parts)

        warnings: list[str] = []
        last_error = ""

        for attempt in range(3):
            if attempt > 0 and last_error:
                user_msg = (
                    f"{request}\n\nPrevious attempt failed validation:\n{last_error}\n"
                    "Please fix the issue and regenerate."
                )
            try:
                response = await self._client.complete(
                    system=system,
                    messages=[{"role": "user", "content": user_msg}],
                    max_tokens=self._max_tokens,
                )
            except LLMError as exc:
                logger.error("LLM error during generate_hcl: %s", exc)
                return GenerationResult(success=False, warnings=[str(exc)])

            raw_text = response.text
            hcl = h.extract_hcl(raw_text)

            if not hcl:
                last_error = "No <terraform> tags found in response."
                warnings.append(f"Attempt {attempt + 1}: {last_error}")
                continue

            validation = hcl_validator.validate_full(hcl)
            if validation.valid:
                return GenerationResult(
                    success=True,
                    hcl=hcl,
                    explanation=h.extract_explanation(raw_text),
                    template_used="ai-generated",
                    variables_applied={"provider": provider},
                    warnings=warnings,
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                )

            violation_msgs = [v.reason for v in validation.violations]
            last_error = "; ".join(violation_msgs + validation.errors)
            warnings.append(f"Attempt {attempt + 1} validation failed: {last_error}")

        return GenerationResult(success=False, warnings=warnings)

    async def explain_plan(self, plan_json: dict[str, Any]) -> str:
        """Explain a terraform plan JSON in plain language."""
        system = explain_prompt.get_prompt()
        user_msg = f"Please explain this Terraform plan:\n\n{json.dumps(plan_json, indent=2)}"
        try:
            response = await self._client.complete(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=self._max_tokens,
            )
        except LLMError as exc:
            logger.error("LLM error during explain_plan: %s", exc)
            return f"Unable to explain plan: {exc}"
        return response.text

    async def diagnose_error(self, error: str, hcl: str) -> DiagnosisResult:
        """Diagnose a terraform error and suggest a corrected HCL fix."""
        h = _helpers()
        system = diagnose_prompt.get_prompt()
        user_msg = (
            f"Terraform error:\n{error}\n\n"
            f"HCL configuration:\n<terraform>\n{hcl}\n</terraform>"
        )
        try:
            response = await self._client.complete(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=self._max_tokens,
            )
        except LLMError as exc:
            logger.error("LLM error during diagnose_error: %s", exc)
            return DiagnosisResult(success=False, root_cause=str(exc))

        text = response.text
        root_cause = h.extract_section(text, "Root Cause")
        explanation = h.extract_section(text, "Explanation")
        fixed_hcl = h.extract_hcl(text)
        fixes = [x for x in (fixed_hcl, explanation) if x]

        return DiagnosisResult(
            success=True,
            root_cause=root_cause or text[:200],
            suggested_fixes=fixes,
            confidence=h.parse_confidence(text),
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

    async def review_hcl(self, hcl: str) -> ReviewResult:
        """Review HCL for security, cost, reliability, and maintainability issues."""
        h = _helpers()
        system = review_prompt.get_prompt()
        user_msg = f"Please review this Terraform configuration:\n\n<terraform>\n{hcl}\n</terraform>"
        try:
            response = await self._client.complete(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=self._max_tokens,
            )
        except LLMError as exc:
            logger.error("LLM error during review_hcl: %s", exc)
            return ReviewResult(success=False)

        text = response.text
        approved = "APPROVED" in text and "REJECTED" not in text

        return ReviewResult(
            success=True,
            approved=approved,
            issues=h.extract_tagged_lines(text, "[ERROR]"),
            suggestions=h.extract_tagged_lines(text, "[INFO]", "[WARNING]"),
            security_concerns=h.extract_tagged_lines(text, "[ERROR] security", "[WARNING] security"),
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a conversational response.

        Yields text delta strings as they arrive from the provider.
        """
        system = chat_prompt.get_prompt(context=context)
        try:
            async for text_delta in self._client.stream(
                system=system,
                messages=messages,
                max_tokens=self._max_tokens,
            ):
                yield text_delta
        except LLMError as exc:
            logger.error("LLM error during chat: %s", exc)
            yield f"Error: {exc}"
