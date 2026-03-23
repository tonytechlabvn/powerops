"""AI-powered remediation engine for failed terraform plan/apply operations (Phase 10).

Wraps LLMClient with automatic error classification, fix generation, and
one-click file patching. Never auto-applies — always returns diffs for user review.
"""
from __future__ import annotations

import logging
from pathlib import Path

from backend.core.llm import LLMError

logger = logging.getLogger(__name__)

_MAX_FILE_CHARS = 4000   # truncate large HCL files before sending to AI
_MAX_RETRIES = 3


def _helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-remediation-helpers.py", "ai_remediation_helpers")


def _ai_helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-agent-helpers.py", "ai_agent_helpers")


def _prompts():
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/remediation-prompt.py", "prompts.remediation_prompt")


class AIRemediationEngine:
    """Diagnoses terraform failures and generates corrected HCL diffs.

    Args:
        client: An LLMClient instance.
        max_tokens: Max tokens for completions.
    """

    def __init__(self, client, max_tokens: int = 4096) -> None:
        self._client = client
        self._max_tokens = max_tokens

    async def diagnose_and_fix(
        self,
        error_output: str,
        workspace_dir: Path,
        failed_operation: str = "plan",
        plan_json: dict | None = None,
    ):
        """Analyze a terraform failure, classify the error, and generate file fixes.

        Returns:
            RemediationResult dataclass with error_category, root_cause, fixes list.
        """
        h = _helpers()
        ai_h = _ai_helpers()

        # Step 1: deterministic classification (fast, no API call)
        error_category = h.classify_error(error_output)

        if not error_category.is_code_fixable:
            return h.RemediationResult(
                error_category=error_category,
                root_cause="This error cannot be fixed by modifying HCL code.",
                is_fixable=False,
                explanation=(
                    "The error is caused by infrastructure, permissions, or state issues "
                    "that require manual intervention outside of your Terraform configuration."
                ),
                confidence=0.9,
            )

        # Step 2: collect workspace HCL files as context
        file_contents = self._collect_hcl_files(workspace_dir)

        # Step 3: call LLM for diagnosis + fix
        system = _prompts().get_prompt()
        hcl_context = "\n\n".join(
            f"--- {fp} ---\n{content}" for fp, content in file_contents.items()
        )
        user_msg = (
            f"Terraform {failed_operation} failed with this error:\n\n{error_output}\n\n"
            f"Workspace HCL files:\n{hcl_context}"
        )

        try:
            response = await self._client.complete(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=self._max_tokens,
            )
        except LLMError as exc:
            logger.error("LLM error during diagnose_and_fix: %s", exc)
            return h.RemediationResult(
                error_category=error_category,
                root_cause=str(exc),
                is_fixable=False,
            )

        text = response.text
        root_cause = ai_h.extract_section(text, "Root Cause")
        explanation = ai_h.extract_section(text, "Explanation")
        fixed_hcl = ai_h.extract_hcl(text)
        confidence = ai_h.parse_confidence(text)

        fixes = self._build_fixes(fixed_hcl, file_contents, ai_h.extract_section(text, "Fix Description"))

        return h.RemediationResult(
            error_category=error_category,
            root_cause=root_cause or text[:200],
            is_fixable=bool(fixes),
            fixes=fixes,
            explanation=explanation,
            confidence=confidence,
        )

    async def apply_fixes(self, workspace_dir: Path, fixes: list):
        """Write fix contents to workspace files. Returns ApplyFixResult.

        Never called automatically — only when the user explicitly clicks Apply.
        """
        h = _helpers()
        result = h.ApplyFixResult()

        for fix in fixes:
            target = workspace_dir / fix.file_path
            try:
                target.write_text(fix.fixed_content, encoding="utf-8")
                result.applied.append(str(fix.file_path))
            except OSError as exc:
                logger.error("Failed to apply fix to %s: %s", fix.file_path, exc)
                result.failed.append(str(fix.file_path))

        # Validate after applying
        if result.applied:
            try:
                from backend.core import hcl_validator
                for applied_path in result.applied:
                    content = (workspace_dir / applied_path).read_text(encoding="utf-8")
                    val = hcl_validator.validate_full(content)
                    if not val.valid:
                        result.validation_errors.extend(val.errors)
            except Exception as exc:
                logger.warning("Post-fix validation skipped: %s", exc)

        return result

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _collect_hcl_files(self, workspace_dir: Path) -> dict[str, str]:
        """Read .tf files from workspace, truncating large ones."""
        files: dict[str, str] = {}
        if not workspace_dir.exists():
            return files
        for tf_file in sorted(workspace_dir.glob("*.tf"))[:8]:
            content = tf_file.read_text(encoding="utf-8", errors="replace")
            if len(content) > _MAX_FILE_CHARS:
                content = content[:_MAX_FILE_CHARS] + "\n# ... truncated ..."
            files[tf_file.name] = content
        return files

    def _build_fixes(self, fixed_hcl: str, originals: dict[str, str], description: str) -> list:
        """Wrap extracted fixed HCL into FileFix objects matched against originals."""
        h = _helpers()
        if not fixed_hcl:
            return []
        target_file = next(iter(originals), "main.tf")
        original = originals.get(target_file, "")
        diff = h.make_unified_diff(original, fixed_hcl, target_file)
        return [h.FileFix(
            file_path=target_file,
            original_content=original,
            fixed_content=fixed_hcl,
            diff_lines=diff,
            description=description or "AI-generated fix",
        )]
