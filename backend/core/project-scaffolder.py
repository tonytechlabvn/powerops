"""Project directory scaffolding — generates starter Terraform files per module.

Creates a directory structure and minimal .tf files for each module in a project,
based on provider type and dependency relationships stored in the database.
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sibling module loader (kebab-case pattern used throughout codebase)
# ---------------------------------------------------------------------------


def _load_sibling(filename: str, alias: str):
    """Load a kebab-case sibling module without going through package __init__."""
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, Path(__file__).parent / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Provider template generators
# ---------------------------------------------------------------------------

_AWS_PROVIDER_BLOCK = """\
provider "aws" {{
  region = var.aws_region
}}
"""

_PROXMOX_PROVIDER_BLOCK = """\
provider "proxmox" {{
  pm_api_url = var.proxmox_url
}}
"""

_GENERIC_PROVIDER_BLOCK = """\
# Configure your provider here
"""


def _provider_block(provider: str) -> str:
    """Return the provider block for a given provider name."""
    p = (provider or "").lower()
    if p == "aws":
        return _AWS_PROVIDER_BLOCK
    if p in ("proxmox", "proxmoxve"):
        return _PROXMOX_PROVIDER_BLOCK
    return _GENERIC_PROVIDER_BLOCK


def _provider_tf_content(provider: str) -> str:
    """Generate provider.tf with required_providers block."""
    p = (provider or "").lower()
    if p == "aws":
        source = "hashicorp/aws"
        version = ">= 5.0"
    elif p in ("proxmox", "proxmoxve"):
        source = "Telmate/proxmox"
        version = ">= 2.9"
    else:
        source = f"hashicorp/{p}" if p else "hashicorp/null"
        version = ">= 1.0"

    return f"""\
terraform {{
  required_providers {{
    {p or "null"} = {{
      source  = "{source}"
      version = "{version}"
    }}
  }}
}}
"""


def _variables_tf_content(provider: str, depends_on_names: list[str]) -> str:
    """Generate variables.tf with provider-specific vars and upstream dependency vars."""
    lines: list[str] = []

    # Provider-specific input variables
    p = (provider or "").lower()
    if p == "aws":
        lines.append('variable "aws_region" {\n  description = "AWS region"\n  default     = "us-east-1"\n}\n')
    elif p in ("proxmox", "proxmoxve"):
        lines.append('variable "proxmox_url" {\n  description = "Proxmox API URL"\n  type        = string\n}\n')

    # Upstream dependency output variables
    for dep_name in depends_on_names:
        safe_dep = dep_name.replace("-", "_").replace(" ", "_")
        lines.append(
            f'variable "upstream_{safe_dep}_id" {{\n'
            f'  description = "Output id from upstream module {dep_name}"\n'
            f'  type        = string\n'
            f'  default     = ""\n'
            f'}}\n'
        )
        lines.append(
            f'variable "upstream_{safe_dep}_output" {{\n'
            f'  description = "Generic output from upstream module {dep_name}"\n'
            f'  type        = string\n'
            f'  default     = ""\n'
            f'}}\n'
        )

    return "\n".join(lines) if lines else "# Add your variables here\n"


def _main_tf_content(module_name: str, provider: str) -> str:
    """Generate main.tf with provider block and placeholder resource."""
    safe_name = module_name.replace("-", "_")
    return (
        f"# Main configuration for module: {module_name}\n\n"
        + _provider_block(provider)
        + f'\n# Add your resources here\n'
        + f'# resource "example" "{safe_name}" {{\n#   ...\n# }}\n'
    )


def _outputs_tf_content(module_name: str) -> str:
    """Generate outputs.tf with placeholder output."""
    safe_name = module_name.replace("-", "_")
    return (
        f"# Outputs for module: {module_name}\n\n"
        f'output "{safe_name}_id" {{\n'
        f'  description = "Resource ID exported by {module_name}"\n'
        f'  value       = ""\n'
        f'}}\n'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scaffold_project(project_id: str, base_dir: Path) -> Path:
    """Generate directory structure from a Project's modules in the database.

    Creates:
        {base_dir}/{project_name}/modules/{provider}/{module_name}/
            main.tf        — provider block + placeholder resource
            variables.tf   — provider vars + upstream dependency vars
            outputs.tf     — placeholder output
            provider.tf    — required_providers block

    Args:
        project_id: UUID of the project to scaffold.
        base_dir:   Root directory under which the project folder is created.

    Returns:
        Path to the created project root directory.

    Raises:
        ValueError: If project not found.
    """
    from backend.db.database import get_session
    from backend.db.models import Project
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import selectinload

    async with get_session() as session:
        project = (await session.execute(
            sa_select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.modules))
        )).scalar_one_or_none()

        if project is None:
            raise ValueError(f"Project '{project_id}' not found")

        project_name = project.name.replace(" ", "-").lower()
        modules = [m for m in (project.modules or []) if m.status != "removed"]

    # Build a name→depends_on map for upstream variable generation
    dep_map: dict[str, list[str]] = {m.name: (m.depends_on or []) for m in modules}

    project_root = base_dir / project_name
    created_dirs: list[Path] = []

    for module in modules:
        provider = (module.provider or "generic").lower()
        module_dir = project_root / "modules" / provider / module.name
        module_dir.mkdir(parents=True, exist_ok=True)
        created_dirs.append(module_dir)

        upstream_deps = dep_map.get(module.name, [])

        # Write the four starter files
        (module_dir / "main.tf").write_text(
            _main_tf_content(module.name, provider), encoding="utf-8"
        )
        (module_dir / "variables.tf").write_text(
            _variables_tf_content(provider, upstream_deps), encoding="utf-8"
        )
        (module_dir / "outputs.tf").write_text(
            _outputs_tf_content(module.name), encoding="utf-8"
        )
        (module_dir / "provider.tf").write_text(
            _provider_tf_content(provider), encoding="utf-8"
        )

        logger.info("Scaffolded module '%s' at %s", module.name, module_dir)

    logger.info(
        "Scaffolded project '%s' (%d modules) at %s",
        project_name, len(created_dirs), project_root,
    )
    return project_root
