"""AI-powered Terraform module generator (Phase 11).

Generates complete multi-file modules from natural language descriptions,
supports iterative refinement, and validates generated HCL files.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

import anthropic

from backend.core.config import Settings

logger = logging.getLogger(__name__)


def _helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-module-generator-helpers.py", "ai_module_generator_helpers")


def _ai_helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-agent-helpers.py", "ai_agent_helpers")


def _prompts():
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/module-generator-prompt.py", "prompts.module_generator_prompt")


class AIModuleGenerator:
    """Generates complete Terraform modules from natural language descriptions.

    Args:
        config: Application Settings instance.
    """

    def __init__(self, config: Settings) -> None:
        if not config.anthropic_api_key:
            raise ValueError("TERRABOT_ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = config.ai_model
        self._max_tokens = config.ai_max_tokens

    async def generate_module(
        self,
        description: str,
        provider: str = "aws",
        complexity: str = "standard",
        additional_context: str | None = None,
    ):
        """Generate a complete module structure from a natural language description.

        Returns:
            GeneratedModule dataclass with files dict keyed by filename.
        """
        h = _helpers()
        ai_h = _ai_helpers()
        system = _prompts().get_prompt(provider=provider)

        user_parts = [
            f"Generate a {complexity} Terraform module for {provider}:\n\n{description}"
        ]
        if additional_context:
            user_parts.append(f"\nAdditional context:\n{additional_context}")
        user_msg = "\n".join(user_parts)

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
        except anthropic.APIError as exc:
            logger.error("Claude API error during generate_module: %s", exc)
            return h.GeneratedModule(name="error", provider=provider, description=str(exc))

        ai_h.log_usage(logger, "generate_module", response.usage)
        raw_text = response.content[0].text if response.content else ""
        files = h.parse_module_files(raw_text)

        module_name = _infer_module_name(description)
        return h.GeneratedModule(
            name=module_name,
            provider=provider,
            description=description,
            files=files,
            resources=_extract_resource_types(files.get("main.tf", "")),
        )

    async def generate_module_streaming(
        self,
        description: str,
        provider: str = "aws",
        complexity: str = "standard",
    ) -> AsyncGenerator:
        """Stream module generation progress, yielding ModuleGenerationEvent objects."""
        h = _helpers()
        ai_h = _ai_helpers()
        system = _prompts().get_prompt(provider=provider)
        user_msg = f"Generate a {complexity} Terraform module for {provider}:\n\n{description}"

        accumulated = ""
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            ) as stream:
                async for delta in stream.text_stream:
                    accumulated += delta
                    yield h.ModuleGenerationEvent(type="file_content", content=delta)
                final = await stream.get_final_message()
                ai_h.log_usage(logger, "generate_module_streaming", final.usage)

            files = h.parse_module_files(accumulated)
            for fname in files:
                yield h.ModuleGenerationEvent(type="file_complete", file_name=fname)
            yield h.ModuleGenerationEvent(type="done")
        except anthropic.APIError as exc:
            logger.error("Claude API error during generate_module_streaming: %s", exc)
            yield h.ModuleGenerationEvent(type="error", content=str(exc))

    async def refine_module(self, current_module, refinement: str):
        """Apply refinement instructions to a previously generated module.

        Args:
            current_module: GeneratedModule dataclass to refine.
            refinement: Natural language description of changes to apply.

        Returns:
            Updated GeneratedModule with revised files.
        """
        h = _helpers()
        ai_h = _ai_helpers()
        system = _prompts().get_prompt(provider=current_module.provider)

        current_files_text = "\n\n".join(
            f'<file name="{fname}">\n{content}\n</file>'
            for fname, content in current_module.files.items()
        )
        user_msg = (
            f"Here is the current module:\n\n{current_files_text}\n\n"
            f"Please apply this refinement and regenerate all files:\n{refinement}"
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
        except anthropic.APIError as exc:
            logger.error("Claude API error during refine_module: %s", exc)
            return current_module

        ai_h.log_usage(logger, "refine_module", response.usage)
        raw_text = response.content[0].text if response.content else ""
        new_files = h.parse_module_files(raw_text)
        if not new_files:
            return current_module

        return h.GeneratedModule(
            name=current_module.name,
            provider=current_module.provider,
            description=current_module.description,
            files=new_files,
            resources=_extract_resource_types(new_files.get("main.tf", "")),
        )

    async def validate_module(self, module):
        """Validate generated module files for HCL syntax and structure."""
        h = _helpers()
        return await _validate_module_files(module.files, h)


# ---------------------------------------------------------------------------
# Module-level helpers (non-methods to reduce class size)
# ---------------------------------------------------------------------------

def _infer_module_name(description: str) -> str:
    import re
    words = re.findall(r"[a-zA-Z]+", description.lower())[:4]
    return "-".join(words) or "generated-module"


def _extract_resource_types(main_tf: str) -> list[str]:
    import re
    matches = re.findall(r'resource\s+"([^"]+)"', main_tf)
    return sorted(set(matches))


async def _validate_module_files(files: dict[str, str], h) -> object:
    """Run HCL validation on all .tf files and structure checks. Returns ModuleValidationResult."""
    file_errors: dict[str, list[str]] = {}
    structure_warnings = h.validate_module_structure(files)
    try:
        from backend.core import hcl_validator
        for fname, content in files.items():
            if not fname.endswith(".tf"):
                continue
            result = hcl_validator.validate_full(content)
            if not result.valid:
                file_errors[fname] = result.errors + [v.reason for v in result.violations]
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("HCL validation skipped: %s", exc)
    return h.ModuleValidationResult(
        valid=not file_errors,
        file_errors=file_errors,
        structure_warnings=structure_warnings,
    )
