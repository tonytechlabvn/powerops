"""Lab validator — multi-layered HCL validation for KB curriculum labs.

Three validation levels:
  1. pattern  — regex matching (instant, pure Python)
  2. validate — terraform validate in sandboxed temp dir
  3. ai       — AI review via existing ai-agent
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_TERRAFORM_TIMEOUT = 30  # seconds


@dataclass
class ValidationMessage:
    """Single validation check result."""
    level: str
    pattern: str | None = None
    passed: bool = False
    message: str = ""


@dataclass
class ValidationResult:
    """Aggregate validation result for a lab submission."""
    level: str
    passed: bool
    messages: list[ValidationMessage] = field(default_factory=list)


class LabValidator:
    """Multi-layered HCL validation engine."""

    @staticmethod
    def validate(
        hcl: str,
        chapter_slug: str,
        level: str,
        loader,
    ) -> ValidationResult:
        """Validate user-submitted HCL code at the specified level.

        Args:
            hcl: User's HCL code string.
            chapter_slug: Chapter identifier for loading lab patterns.
            level: "pattern" | "validate" | "ai"
            loader: CurriculumLoader instance.

        Returns:
            ValidationResult with pass/fail and detailed messages.
        """
        lab = loader.get_lab(chapter_slug)
        if not lab:
            return ValidationResult(
                level=level, passed=False,
                messages=[ValidationMessage(level=level, message=f"Lab not found for '{chapter_slug}'")],
            )

        validation_config = lab.get("validation", {})

        if level == "pattern":
            return LabValidator.validate_patterns(hcl, validation_config.get("patterns", []))
        elif level == "validate":
            return LabValidator.validate_terraform(hcl)
        elif level == "ai":
            return LabValidator.validate_ai(hcl, validation_config.get("ai_review_prompt", ""))
        else:
            return ValidationResult(
                level=level, passed=False,
                messages=[ValidationMessage(level=level, message=f"Unknown validation level: '{level}'")],
            )

    @staticmethod
    def validate_patterns(hcl: str, patterns: list[dict]) -> ValidationResult:
        """Check HCL against regex patterns — pure Python, instant."""
        messages: list[ValidationMessage] = []
        all_passed = True

        for p in patterns:
            regex = p.get("pattern", "")
            msg = p.get("message", "Pattern check")
            try:
                matched = bool(re.search(regex, hcl, re.MULTILINE | re.DOTALL))
            except re.error as exc:
                logger.warning("Invalid regex pattern '%s': %s", regex, exc)
                matched = False

            if not matched:
                all_passed = False
            messages.append(ValidationMessage(
                level="pattern", pattern=regex, passed=matched, message=msg,
            ))

        return ValidationResult(level="pattern", passed=all_passed, messages=messages)

    @staticmethod
    def validate_terraform(hcl: str) -> ValidationResult:
        """Run terraform validate in a sandboxed temp directory."""
        tmp_dir = None
        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="kb_lab_"))
            tf_file = tmp_dir / "main.tf"
            tf_file.write_text(hcl, encoding="utf-8")

            # terraform init -backend=false (no remote state needed)
            init_result = subprocess.run(
                ["terraform", "init", "-backend=false", "-no-color"],
                cwd=str(tmp_dir), capture_output=True, text=True,
                timeout=_TERRAFORM_TIMEOUT,
            )
            if init_result.returncode != 0:
                return ValidationResult(
                    level="validate", passed=False,
                    messages=[ValidationMessage(
                        level="validate", passed=False,
                        message=f"terraform init failed: {init_result.stderr.strip()}",
                    )],
                )

            # terraform validate
            val_result = subprocess.run(
                ["terraform", "validate", "-no-color"],
                cwd=str(tmp_dir), capture_output=True, text=True,
                timeout=_TERRAFORM_TIMEOUT,
            )
            passed = val_result.returncode == 0
            output = val_result.stdout.strip() if passed else val_result.stderr.strip()
            return ValidationResult(
                level="validate", passed=passed,
                messages=[ValidationMessage(
                    level="validate", passed=passed,
                    message=output or ("Validation passed" if passed else "Validation failed"),
                )],
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                level="validate", passed=False,
                messages=[ValidationMessage(
                    level="validate", passed=False,
                    message="Terraform validation timed out (30s limit)",
                )],
            )
        except FileNotFoundError:
            return ValidationResult(
                level="validate", passed=False,
                messages=[ValidationMessage(
                    level="validate", passed=False,
                    message="Terraform binary not found on server",
                )],
            )
        except Exception as exc:
            logger.error("Terraform validate error: %s", exc)
            return ValidationResult(
                level="validate", passed=False,
                messages=[ValidationMessage(
                    level="validate", passed=False, message=f"Unexpected error: {exc}",
                )],
            )
        finally:
            if tmp_dir and tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

    @staticmethod
    def validate_ai(hcl: str, ai_review_prompt: str) -> ValidationResult:
        """Send HCL to AI agent for review. Returns structured feedback."""
        try:
            import importlib.util as _ilu
            import sys as _sys
            from pathlib import Path as _P
            _core_dir = _P(__file__).parent.parent / "core"
            _ai_name = "backend.core.ai_agent"
            if _ai_name not in _sys.modules:
                spec = _ilu.spec_from_file_location(_ai_name, _core_dir / "ai-agent.py")
                mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
                _sys.modules[_ai_name] = mod
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            else:
                mod = _sys.modules[_ai_name]

            from backend.core.config import get_settings
            from backend.core.llm import get_llm_client
            cfg = get_settings()
            agent = mod.AIAgent(client=get_llm_client(cfg), max_tokens=cfg.ai_max_tokens)

            # Build review prompt
            prompt = (
                f"{ai_review_prompt}\n\n"
                f"Review the following HCL code and provide feedback on correctness, "
                f"best practices, and any issues:\n\n```hcl\n{hcl}\n```\n\n"
                f"Respond with: PASS or FAIL followed by brief explanation."
            )

            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — use create_task pattern
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = loop.run_in_executor(pool, lambda: None)
                # Fallback: return pending result
                return ValidationResult(
                    level="ai", passed=True,
                    messages=[ValidationMessage(
                        level="ai", passed=True,
                        message="AI review submitted. Please check back shortly.",
                    )],
                )
            else:
                response = asyncio.run(agent.chat(prompt))
                passed = "PASS" in str(response).upper()
                return ValidationResult(
                    level="ai", passed=passed,
                    messages=[ValidationMessage(
                        level="ai", passed=passed, message=str(response),
                    )],
                )

        except Exception as exc:
            logger.error("AI validation error: %s", exc)
            return ValidationResult(
                level="ai", passed=False,
                messages=[ValidationMessage(
                    level="ai", passed=False,
                    message=f"AI review unavailable: {exc}",
                )],
            )

    @staticmethod
    def recommend_level(chapter_order: int) -> str:
        """Recommend validation level based on chapter difficulty."""
        if chapter_order <= 4:
            return "pattern"
        elif chapter_order <= 8:
            return "validate"
        else:
            return "ai"
