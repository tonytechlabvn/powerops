"""Module documentation generator.

Generates structured documentation by parsing a module zip archive:
  - README.md → raw markdown
  - variables.tf → typed variable table
  - outputs.tf → output table
  - *.tf resource blocks → resource inventory
  - examples/ directory → code examples
  - HCL usage snippet auto-generated from required variables
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VariableDoc:
    name: str
    type: str
    description: str
    default: str | None
    required: bool
    validation: str | None = None


@dataclass
class OutputDoc:
    name: str
    description: str
    value: str


@dataclass
class ResourceDoc:
    type: str
    name: str
    provider: str


@dataclass
class ExampleDoc:
    name: str
    description: str
    code: str


@dataclass
class ModuleDocumentation:
    readme: str
    variables: list[VariableDoc] = field(default_factory=list)
    outputs: list[OutputDoc] = field(default_factory=list)
    resources: list[ResourceDoc] = field(default_factory=list)
    usage_example: str = ""
    examples: list[ExampleDoc] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Lazy-load parser
# ---------------------------------------------------------------------------

def _parser():
    alias = "backend.core.module_registry_parser"
    if alias in _sys.modules:
        return _sys.modules[alias]
    spec = _ilu.spec_from_file_location(
        alias, Path(__file__).resolve().parent / "module-registry-parser.py"
    )
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class ModuleDocsGenerator:
    """Generates structured documentation from a module zip archive."""

    def generate(self, zip_path: Path, module_address: str = "") -> ModuleDocumentation:
        """Parse archive and return full ModuleDocumentation."""
        p = _parser()

        raw_vars = p.extract_variables(zip_path)
        raw_outputs = p.extract_outputs(zip_path)
        raw_resources = p.extract_resources(zip_path)
        readme = p.extract_readme(zip_path)

        variables = [self._map_variable(v) for v in raw_vars]
        outputs = [self._map_output(o) for o in raw_outputs]
        resources = [self._map_resource(r) for r in raw_resources]
        examples = self._parse_examples(zip_path)

        usage = ""
        if module_address:
            usage = p.generate_usage_example(module_address, raw_vars)

        return ModuleDocumentation(
            readme=readme,
            variables=variables,
            outputs=outputs,
            resources=resources,
            usage_example=usage,
            examples=examples,
        )

    # ------------------------------------------------------------------
    # Internal mappers
    # ------------------------------------------------------------------

    def _map_variable(self, raw: dict) -> VariableDoc:
        default = raw.get("default")
        default_str = None if default is None else str(default)
        return VariableDoc(
            name=raw.get("name", ""),
            type=raw.get("type", "any"),
            description=raw.get("description", ""),
            default=default_str,
            required=raw.get("required", default is None),
            validation=raw.get("validation"),
        )

    def _map_output(self, raw: dict) -> OutputDoc:
        return OutputDoc(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            value=raw.get("value", ""),
        )

    def _map_resource(self, raw: dict) -> ResourceDoc:
        return ResourceDoc(
            type=raw.get("type", ""),
            name=raw.get("name", ""),
            provider=raw.get("provider", ""),
        )

    def _parse_examples(self, zip_path: Path) -> list[ExampleDoc]:
        """Scan the examples/ directory inside the archive."""
        examples: list[ExampleDoc] = []
        try:
            with zipfile.ZipFile(zip_path) as zf:
                example_files = [
                    n for n in zf.namelist()
                    if "examples/" in n and n.endswith(".tf")
                ]
                # Group by example sub-directory
                dirs: dict[str, list[str]] = {}
                for name in example_files:
                    parts = name.split("/")
                    # examples/subdir/main.tf → key = "subdir"
                    ex_name = parts[-2] if len(parts) > 2 else "default"
                    dirs.setdefault(ex_name, []).append(name)

                for ex_name, files in sorted(dirs.items()):
                    code_parts = []
                    for fname in sorted(files):
                        code_parts.append(f"# {fname.split('/')[-1]}")
                        code_parts.append(zf.read(fname).decode("utf-8", errors="replace"))
                    examples.append(ExampleDoc(
                        name=ex_name,
                        description=f"Example: {ex_name}",
                        code="\n".join(code_parts),
                    ))
        except Exception as exc:
            logger.warning("Failed to parse examples from archive: %s", exc)
        return examples


# ---------------------------------------------------------------------------
# Convenience: render docs as markdown
# ---------------------------------------------------------------------------

def render_markdown(docs: ModuleDocumentation) -> str:
    """Render ModuleDocumentation to a markdown string."""
    parts: list[str] = []

    if docs.readme:
        parts.append(docs.readme)
        parts.append("")

    if docs.usage_example:
        parts.append("## Usage")
        parts.append("```hcl")
        parts.append(docs.usage_example)
        parts.append("```")
        parts.append("")

    if docs.variables:
        parts.append("## Inputs")
        parts.append("")
        parts.append("| Name | Type | Description | Default | Required |")
        parts.append("|------|------|-------------|---------|----------|")
        for v in docs.variables:
            default = v.default if v.default is not None else "n/a"
            required = "yes" if v.required else "no"
            desc = v.description.replace("|", "\\|")
            parts.append(f"| {v.name} | `{v.type}` | {desc} | `{default}` | {required} |")
        parts.append("")

    if docs.outputs:
        parts.append("## Outputs")
        parts.append("")
        parts.append("| Name | Description |")
        parts.append("|------|-------------|")
        for o in docs.outputs:
            parts.append(f"| {o.name} | {o.description} |")
        parts.append("")

    if docs.resources:
        parts.append("## Resources")
        parts.append("")
        parts.append("| Type | Name |")
        parts.append("|------|------|")
        for r in docs.resources:
            parts.append(f"| {r.type} | {r.name} |")
        parts.append("")

    return "\n".join(parts)
