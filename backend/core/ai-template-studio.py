"""AI-powered Jinja2 template studio.

Generates complete template packages (main.tf.j2 + variables.json + metadata.json)
from natural language descriptions, extracts templates from raw HCL, and supports
iterative chat refinement.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import anthropic

from backend.core.config import Settings

logger = logging.getLogger(__name__)


def _helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-template-studio-helpers.py", "ai_template_studio_helpers")


def _ai_helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-agent-helpers.py", "ai_agent_helpers")


def _prompts():
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/template-studio-prompt.py", "prompts.template_studio_prompt")


def _wizard_prompts():
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/wizard-step-prompt.py", "prompts.wizard_step_prompt")


# Sanitise template names to prevent path traversal
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-/]*$")


class AITemplateStudio:
    """Generates Jinja2 template packages from NL descriptions or raw HCL.

    Args:
        config: Application Settings instance.
    """

    def __init__(self, config: Settings) -> None:
        if not config.anthropic_api_key:
            raise ValueError("TERRABOT_ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = config.ai_model
        self._max_tokens = config.ai_max_tokens
        self._template_dir = Path(config.template_dir)

    # ------------------------------------------------------------------
    # Generate: NL description → template package
    # ------------------------------------------------------------------

    async def generate_template(
        self,
        description: str,
        providers: list[str] | None = None,
        complexity: str = "standard",
        additional_context: str | None = None,
    ):
        """Generate a complete Jinja2 template package from NL description."""
        h = _helpers()
        ai_h = _ai_helpers()
        providers = providers or ["aws"]
        system = _prompts().get_generate_prompt(providers=providers, complexity=complexity)

        user_parts = [f"Generate a Jinja2 template package:\n\n{description}"]
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
            logger.error("Claude API error during generate_template: %s", exc)
            return h.GeneratedTemplate(name="error", providers=providers, description=str(exc))

        ai_h.log_usage(logger, "generate_template", response.usage)
        raw_text = response.content[0].text if response.content else ""
        files = h.parse_template_files(raw_text)
        meta = _extract_metadata(files)

        return h.GeneratedTemplate(
            name=meta.get("name", _infer_template_name(description, providers)),
            providers=providers,
            description=description,
            files=files,
            display_name=meta.get("display_name", ""),
            tags=meta.get("tags", []),
            version=meta.get("version", "1.0.0"),
        )

    # ------------------------------------------------------------------
    # Extract: raw HCL → template package
    # ------------------------------------------------------------------

    async def extract_template(self, hcl_code: str, template_name: str | None = None):
        """Extract a Jinja2 template from raw HCL by parameterising hardcoded values."""
        h = _helpers()
        ai_h = _ai_helpers()
        system = _prompts().get_extract_prompt()

        user_msg = f"Convert this HCL into a Jinja2 template package:\n\n{hcl_code}"
        if template_name:
            user_msg += f"\n\nTemplate name: {template_name}"

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
        except anthropic.APIError as exc:
            logger.error("Claude API error during extract_template: %s", exc)
            return h.GeneratedTemplate(name="error", providers=[], description=str(exc))

        ai_h.log_usage(logger, "extract_template", response.usage)
        raw_text = response.content[0].text if response.content else ""
        files = h.parse_template_files(raw_text)
        meta = _extract_metadata(files)
        providers = [meta.get("provider", "aws")] if meta.get("provider") else ["aws"]

        return h.GeneratedTemplate(
            name=template_name or meta.get("name", "extracted-template"),
            providers=providers,
            description=meta.get("description", "Extracted from HCL"),
            files=files,
            display_name=meta.get("display_name", ""),
            tags=meta.get("tags", []),
        )

    # ------------------------------------------------------------------
    # Refine: iterative refinement with conversation history
    # ------------------------------------------------------------------

    async def refine_template(
        self,
        current_template,
        refinement: str,
        conversation_history: list[dict] | None = None,
    ):
        """Apply refinement instructions to a template, preserving conversation context."""
        h = _helpers()
        ai_h = _ai_helpers()
        system = _prompts().get_refine_prompt()

        current_files_text = "\n\n".join(
            f'<file name="{fname}">\n{content}\n</file>'
            for fname, content in current_template.files.items()
        )

        # Build messages with conversation history for multi-turn context
        # Security: validate roles to prevent prompt injection via "system" messages
        messages: list[dict] = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role in ("user", "assistant") and isinstance(content, str):
                    messages.append({"role": role, "content": content})
        messages.append({
            "role": "user",
            "content": (
                f"Here is the current template:\n\n{current_files_text}\n\n"
                f"Please apply this refinement and regenerate all files:\n{refinement}"
            ),
        })

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=messages,
            )
        except anthropic.APIError as exc:
            logger.error("Claude API error during refine_template: %s", exc)
            return current_template

        ai_h.log_usage(logger, "refine_template", response.usage)
        raw_text = response.content[0].text if response.content else ""
        new_files = h.parse_template_files(raw_text)
        if not new_files:
            return current_template

        meta = _extract_metadata(new_files)
        return h.GeneratedTemplate(
            name=current_template.name,
            providers=current_template.providers,
            description=current_template.description,
            files=new_files,
            display_name=meta.get("display_name", current_template.display_name),
            tags=meta.get("tags", current_template.tags),
            version=current_template.version,
        )

    # ------------------------------------------------------------------
    # Wizard: analyze description → applicable steps with defaults
    # ------------------------------------------------------------------

    async def analyze_wizard_steps(self, description: str) -> dict:
        """Analyze NL description and return applicable wizard steps with defaults.

        Returns dict with keys: steps (list[str]), defaults (dict), reasoning (str).
        """
        ai_h = _ai_helpers()
        system = _wizard_prompts().get_wizard_step_prompt()

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": description}],
            )
        except anthropic.APIError as exc:
            logger.error("Claude API error during analyze_wizard_steps: %s", exc)
            return {"steps": ["provider", "review"], "defaults": {}, "reasoning": str(exc)}

        ai_h.log_usage(logger, "analyze_wizard_steps", response.usage)
        raw_text = response.content[0].text if response.content else ""

        # Parse JSON from response
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try extracting JSON from code fence
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except json.JSONDecodeError:
                    result = {"steps": ["provider", "review"], "defaults": {}, "reasoning": "Parse error"}
            else:
                result = {"steps": ["provider", "review"], "defaults": {}, "reasoning": "Parse error"}

        # Validate steps against known set
        valid_steps = {"provider", "compute", "networking", "storage", "security", "connectivity", "monitoring", "review"}
        result["steps"] = [s for s in result.get("steps", []) if s in valid_steps]
        if "provider" not in result["steps"]:
            result["steps"].insert(0, "provider")
        if "review" not in result["steps"]:
            result["steps"].append("review")

        return result

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save_template(self, template, overwrite: bool = False) -> str:
        """Write template files to templates/{provider}/{name}/ on disk.

        Returns the saved directory path as string.
        Raises ValueError on invalid name or existing template without overwrite.
        """
        _validate_template_name(template.name)

        # Derive provider directory from template name (e.g. "hybrid/my-vpn" → "hybrid")
        parts = template.name.split("/", 1)
        if len(parts) == 2:
            template_path = self._template_dir / template.name
        else:
            provider = template.providers[0] if template.providers else "custom"
            template_path = self._template_dir / provider / template.name

        if template_path.exists() and not overwrite:
            raise ValueError(f"Template already exists: {template.name}. Use overwrite=True.")

        template_path.mkdir(parents=True, exist_ok=True)

        for fname, content in template.files.items():
            file_path = (template_path / fname).resolve()
            # Security: ensure resolved path stays within the template directory
            if not str(file_path).startswith(str(template_path.resolve())):
                raise ValueError(f"Invalid file path (path traversal): {fname}")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        logger.info("Saved template to %s (%d files)", template_path, len(template.files))
        return str(template_path)

    def load_template(self, name: str):
        """Read a template directory and reconstruct a GeneratedTemplate.

        Returns None if template not found.
        """
        h = _helpers()
        _validate_template_name(name)
        template_path = self._template_dir / name

        if not template_path.is_dir():
            return None

        files: dict[str, str] = {}
        for file_path in template_path.rglob("*"):
            if file_path.is_file() and file_path.name != ".gitignore":
                rel = str(file_path.relative_to(template_path)).replace("\\", "/")
                files[rel] = file_path.read_text(encoding="utf-8")

        meta = _extract_metadata(files)
        parts = name.split("/")
        providers = [meta.get("provider", parts[0])] if meta.get("provider") else [parts[0]]

        return h.GeneratedTemplate(
            name=name,
            providers=providers,
            description=meta.get("description", ""),
            files=files,
            display_name=meta.get("display_name", parts[-1] if parts else name),
            tags=meta.get("tags", []),
            version=meta.get("version", "1.0.0"),
        )

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    async def validate_template(self, template) -> object:
        """Validate Jinja2 syntax, rendered HCL, and template structure."""
        h = _helpers()

        # 1. Structure check
        structure_warnings = h.validate_template_structure(template.files)

        # 2. Jinja2 syntax check on main.tf.j2
        jinja2_errors: list[str] = []
        main_content = template.files.get("main.tf.j2", "")
        if main_content:
            jinja2_errors = h.validate_jinja2_syntax(main_content)

        # 3. HCL validation after rendering with defaults
        hcl_errors: dict[str, list[str]] = {}
        if main_content and not jinja2_errors:
            hcl_errors = _validate_rendered_hcl(main_content, template.files)

        return h.TemplateValidationResult(
            valid=not jinja2_errors and not hcl_errors,
            jinja2_errors=jinja2_errors,
            hcl_errors=hcl_errors,
            structure_warnings=structure_warnings,
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _validate_template_name(name: str) -> None:
    """Raise ValueError if name contains path traversal or invalid characters."""
    if ".." in name or name.startswith("/") or name.startswith("\\"):
        raise ValueError(f"Invalid template name (path traversal): {name}")
    if not _SAFE_NAME_RE.match(name.replace(".", "-").replace("/", "-").split("/")[0]):
        raise ValueError(f"Invalid template name: {name}")


def _infer_template_name(description: str, providers: list[str]) -> str:
    """Generate a kebab-case template name from description."""
    words = re.findall(r"[a-zA-Z]+", description.lower())[:4]
    slug = "-".join(words) or "generated-template"
    provider = "hybrid" if len(providers) > 1 else providers[0].lower()
    return f"{provider}/{slug}"


def _extract_metadata(files: dict[str, str]) -> dict:
    """Parse metadata.json from files dict if present."""
    raw = files.get("metadata.json", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _validate_rendered_hcl(main_j2: str, files: dict[str, str]) -> dict[str, list[str]]:
    """Render main.tf.j2 with variable defaults and validate the HCL output."""
    h = _helpers()
    hcl_errors: dict[str, list[str]] = {}

    # Build defaults from variables.json
    defaults: dict[str, object] = {}
    vars_raw = files.get("variables.json", "")
    variables = h.parse_variables_json(vars_raw)
    for var in variables:
        if "default" in var and var["default"] is not None:
            defaults[var["name"]] = var["default"]

    # Render with defaults
    try:
        from jinja2 import Environment, StrictUndefined, UndefinedError
        env = Environment(
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        tmpl = env.from_string(main_j2)
        rendered = tmpl.render(**defaults)
    except UndefinedError as exc:
        hcl_errors["main.tf.j2"] = [f"Undefined variable during render: {exc}"]
        return hcl_errors
    except Exception as exc:
        hcl_errors["main.tf.j2"] = [f"Render error: {exc}"]
        return hcl_errors

    # Validate rendered HCL
    try:
        from backend.core import hcl_validator
        result = hcl_validator.validate_full(rendered)
        if not result.valid:
            hcl_errors["main.tf (rendered)"] = result.errors + [
                v.reason for v in getattr(result, "violations", [])
            ]
    except Exception as exc:
        logger.debug("HCL validation skipped: %s", exc)

    return hcl_errors
