"""Parse and validate project.yaml config into structured data.

Validates module dependencies form a DAG (no cycles), provider names,
and role definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class ModuleConfig:
    name: str
    path: str
    provider: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class RoleConfig:
    name: str
    permissions: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)


@dataclass
class OutputConfig:
    name: str
    module: str
    description: str = ""


@dataclass
class HcpTerraformConfig:
    organization: str = ""
    workspace: str = ""
    execution_mode: str = "local"


@dataclass
class ProjectConfig:
    name: str
    description: str = ""
    version: str = "1.0"
    providers: list[str] = field(default_factory=list)
    modules: list[ModuleConfig] = field(default_factory=list)
    roles: list[RoleConfig] = field(default_factory=list)
    outputs: list[OutputConfig] = field(default_factory=list)
    hcp_terraform: Optional[HcpTerraformConfig] = None


class ProjectConfigError(Exception):
    """Raised when project.yaml is invalid."""
    pass


def parse_project_yaml(yaml_content: str) -> ProjectConfig:
    """Parse raw YAML string into validated ProjectConfig."""
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ProjectConfigError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise ProjectConfigError("Project config must be a YAML mapping")

    name = data.get("name")
    if not name or not isinstance(name, str):
        raise ProjectConfigError("Project config requires a 'name' field")

    # Parse modules
    modules = []
    for m in data.get("modules", []):
        if not isinstance(m, dict) or "name" not in m:
            raise ProjectConfigError(f"Each module must have a 'name': {m}")
        modules.append(ModuleConfig(
            name=m["name"],
            path=m.get("path", f"modules/{m['name']}"),
            provider=m.get("provider", ""),
            depends_on=m.get("depends_on", []),
        ))

    # Validate DAG (no cycles in depends_on)
    _validate_dag(modules)

    # Parse roles
    roles = []
    for r in data.get("roles", []):
        if not isinstance(r, dict) or "name" not in r:
            raise ProjectConfigError(f"Each role must have a 'name': {r}")
        roles.append(RoleConfig(
            name=r["name"],
            permissions=r.get("permissions", []),
            modules=r.get("modules", []),
        ))

    # Parse outputs
    outputs = []
    for o in data.get("outputs", []):
        if not isinstance(o, dict) or "name" not in o:
            raise ProjectConfigError(f"Each output must have a 'name': {o}")
        outputs.append(OutputConfig(
            name=o["name"],
            module=o.get("module", ""),
            description=o.get("description", ""),
        ))

    # Parse HCP Terraform config
    hcp = None
    if "hcp_terraform" in data:
        h = data["hcp_terraform"]
        hcp = HcpTerraformConfig(
            organization=h.get("organization", ""),
            workspace=h.get("workspace", ""),
            execution_mode=h.get("execution_mode", "local"),
        )

    return ProjectConfig(
        name=name,
        description=data.get("description", ""),
        version=str(data.get("version", "1.0")),
        providers=data.get("providers", []),
        modules=modules,
        roles=roles,
        outputs=outputs,
        hcp_terraform=hcp,
    )


def _validate_dag(modules: list[ModuleConfig]) -> None:
    """Ensure module dependencies form a directed acyclic graph."""
    module_names = {m.name for m in modules}

    # Check all depends_on reference existing modules
    for m in modules:
        for dep in m.depends_on:
            if dep not in module_names:
                raise ProjectConfigError(
                    f"Module '{m.name}' depends on unknown module '{dep}'"
                )

    # Topological sort to detect cycles
    visited: set[str] = set()
    in_stack: set[str] = set()
    dep_map = {m.name: m.depends_on for m in modules}

    def _visit(name: str) -> None:
        if name in in_stack:
            raise ProjectConfigError(f"Circular dependency detected involving '{name}'")
        if name in visited:
            return
        in_stack.add(name)
        for dep in dep_map.get(name, []):
            _visit(dep)
        in_stack.discard(name)
        visited.add(name)

    for m in modules:
        _visit(m.name)
