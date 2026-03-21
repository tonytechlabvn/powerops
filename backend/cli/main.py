"""TerraBot CLI entry point — Typer app with Rich output.

Entry point registered in pyproject.toml:
    [project.scripts]
    terrabot = "backend.cli.main:app"

All kebab-case command modules are loaded via cli-loader.py so that
standard Python import machinery can resolve them despite the hyphens.
"""
from __future__ import annotations

import logging
from typing import Optional

import typer
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Load kebab-case command modules via importlib
# ---------------------------------------------------------------------------

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_COMMANDS_DIR = _Path(__file__).parent / "commands"


def _load_cmd(filename: str, alias: str):
    """Load a kebab-case command module idempotently."""
    full_name = f"backend.cli.commands.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, _COMMANDS_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load command: {filename}")
    mod = _ilu.module_from_spec(spec)
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# Pre-load all command modules — original
_init_cmd    = _load_cmd("init-command.py",    "init_command")
_plan_cmd    = _load_cmd("plan-command.py",    "plan_command")
_apply_cmd   = _load_cmd("apply-command.py",   "apply_command")
_destroy_cmd = _load_cmd("destroy-command.py", "destroy_command")
_status_cmd  = _load_cmd("status-command.py",  "status_command")
_explain_cmd = _load_cmd("explain-command.py", "explain_command")

# Template sub-app loaded separately
_tmpl_cmd = _load_cmd("template-command.py", "template_command")

# Phase 7 — advanced feature command modules
_drift_cmd     = _load_cmd("drift-command.py",     "drift_command")
_workspace_cmd = _load_cmd("workspace-command.py", "workspace_command")
_import_cmd    = _load_cmd("import-command.py",    "import_command")

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="terrabot",
    help="[bold cyan]TerraBot[/bold cyan] — AI-powered Terraform automation platform.",
    rich_markup_mode="rich",
    no_args_is_help=True,
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
)

# Template sub-app
template_app = typer.Typer(
    name="template",
    help="Browse and render Terraform templates.",
    no_args_is_help=True,
)
app.add_typer(template_app, name="template")

# Drift sub-app
drift_app = typer.Typer(
    name="drift",
    help="Detect and review infrastructure drift.",
    no_args_is_help=True,
)
app.add_typer(drift_app, name="drift")

# Workspace sub-app
workspace_app = typer.Typer(
    name="workspace",
    help="Manage multiple Terraform workspaces.",
    no_args_is_help=True,
)
app.add_typer(workspace_app, name="workspace")

# Import sub-app
import_app = typer.Typer(
    name="import",
    help="Import existing infrastructure into Terraform state.",
    no_args_is_help=True,
)
app.add_typer(import_app, name="import")

# ---------------------------------------------------------------------------
# Global callback for --verbose flag
# ---------------------------------------------------------------------------

@app.callback()
def global_options(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging", is_eager=False),
) -> None:
    """TerraBot — manage Terraform workspaces with AI assistance."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------

@app.command("init")
def cmd_init(
    workspace: str = typer.Option("./workspaces", "--workspace", "-w", help="Workspace directory"),
    provider: str = typer.Option("", "--provider", "-p", help="Provider: aws or proxmox"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Interactive project initialisation wizard."""
    _init_cmd.run(workspace=workspace, provider=provider, json_output=json_output, verbose=verbose)


@app.command("plan")
def cmd_plan(
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    var_file: Optional[str] = typer.Option(None, "--var-file", help="Path to .tfvars file"),
    out: Optional[str] = typer.Option(None, "--out", help="Save plan binary to this path"),
    destroy: bool = typer.Option(False, "--destroy", help="Plan a destroy operation"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Run terraform plan and display a Rich diff of planned changes."""
    _plan_cmd.run(
        working_dir=working_dir,
        var_file=var_file,
        out=out,
        destroy=destroy,
        json_output=json_output,
        verbose=verbose,
    )


@app.command("apply")
def cmd_apply(
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    plan_file: Optional[str] = typer.Option(None, "--plan-file", help="Path to saved plan binary"),
    var_file: Optional[str] = typer.Option(None, "--var-file", help="Path to .tfvars file"),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Apply terraform changes with a confirmation prompt."""
    _apply_cmd.run(
        working_dir=working_dir,
        plan_file=plan_file,
        var_file=var_file,
        auto_approve=auto_approve,
        json_output=json_output,
        verbose=verbose,
    )


@app.command("destroy")
def cmd_destroy(
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    var_file: Optional[str] = typer.Option(None, "--var-file", help="Path to .tfvars file"),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip confirmation prompts"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Destroy all terraform-managed infrastructure (requires double confirmation)."""
    _destroy_cmd.run(
        working_dir=working_dir,
        var_file=var_file,
        auto_approve=auto_approve,
        json_output=json_output,
        verbose=verbose,
    )


@app.command("status")
def cmd_status(
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Display current workspace status and terraform state summary."""
    _status_cmd.run(working_dir=working_dir, json_output=json_output, verbose=verbose)


@app.command("explain")
def cmd_explain(
    term: str = typer.Argument(..., help="Terraform term or concept to explain"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Explain a Terraform concept using AI."""
    _explain_cmd.run(term=term, json_output=json_output, verbose=verbose)


# ---------------------------------------------------------------------------
# Template sub-commands
# ---------------------------------------------------------------------------

@template_app.command("list")
def cmd_template_list(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter: aws or proxmox"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """List all available TerraBot templates."""
    _tmpl_cmd.list_templates(provider=provider, json_output=json_output, verbose=verbose)


@template_app.command("use")
def cmd_template_use(
    name: str = typer.Argument(..., help="Template name, e.g. aws/ec2-web-server"),
    var: list[str] = typer.Option([], "--var", help="Variable overrides: key=value (repeatable)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write rendered HCL to file"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Render a template to HCL, prompting interactively for missing variables."""
    _tmpl_cmd.use_template(name=name, var=var, output=output, json_output=json_output, verbose=verbose)


@template_app.command("info")
def cmd_template_info(
    name: str = typer.Argument(..., help="Template name, e.g. aws/ec2-web-server"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Show detailed information about a specific template."""
    _tmpl_cmd.template_info(name=name, json_output=json_output, verbose=verbose)


# ---------------------------------------------------------------------------
# Drift sub-commands
# ---------------------------------------------------------------------------

@drift_app.command("check")
def cmd_drift_check(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Logical workspace name"),
    workspace_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Run a drift check against live infrastructure."""
    _drift_cmd.check(workspace=workspace, workspace_dir=workspace_dir, json_output=json_output)


@drift_app.command("history")
def cmd_drift_history(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Logical workspace name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Show past drift check results for a workspace."""
    _drift_cmd.history(workspace=workspace, limit=limit, json_output=json_output)


# ---------------------------------------------------------------------------
# Workspace sub-commands
# ---------------------------------------------------------------------------

@workspace_app.command("create")
def cmd_workspace_create(
    name: str = typer.Argument(..., help="Workspace name"),
    provider: str = typer.Option("", "--provider", "-p", help="Cloud provider"),
    environment: str = typer.Option("", "--env", "-e", help="Environment label"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Create a new Terraform workspace."""
    _workspace_cmd.create(name=name, provider=provider, environment=environment, json_output=json_output)


@workspace_app.command("list")
def cmd_workspace_list(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """List all registered workspaces."""
    _workspace_cmd.list_workspaces(json_output=json_output)


@workspace_app.command("switch")
def cmd_workspace_switch(
    name: str = typer.Argument(..., help="Workspace name to switch to"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Switch the active Terraform workspace."""
    _workspace_cmd.switch(name=name, json_output=json_output)


@workspace_app.command("delete")
def cmd_workspace_delete(
    name: str = typer.Argument(..., help="Workspace name to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Delete a workspace and its directory."""
    _workspace_cmd.delete(name=name, yes=yes, json_output=json_output)


@workspace_app.command("current")
def cmd_workspace_current(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Show the currently active workspace."""
    _workspace_cmd.current(json_output=json_output)


# ---------------------------------------------------------------------------
# Import sub-commands
# ---------------------------------------------------------------------------

@import_app.command("resource")
def cmd_import_resource(
    resource_type: str = typer.Argument(..., help="Terraform resource type, e.g. aws_instance"),
    resource_id: str = typer.Argument(..., help="Provider resource ID, e.g. i-0abc123"),
    tf_address: str = typer.Argument(..., help="Terraform address, e.g. aws_instance.web"),
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Import a single existing resource into Terraform state."""
    _import_cmd.resource(
        resource_type=resource_type,
        resource_id=resource_id,
        tf_address=tf_address,
        working_dir=working_dir,
        json_output=json_output,
    )


@import_app.command("bulk")
def cmd_import_bulk(
    mapping_file: str = typer.Argument(..., help="JSON file with import mapping list"),
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Import multiple resources from a JSON mapping file."""
    _import_cmd.bulk(mapping_file=mapping_file, working_dir=working_dir, json_output=json_output)


@import_app.command("config")
def cmd_import_config(
    resource_type: str = typer.Argument(..., help="Terraform resource type, e.g. aws_instance"),
    resource_id: str = typer.Argument(..., help="Provider resource ID for reference"),
    tf_name: str = typer.Option("imported", "--name", "-n", help="Terraform logical resource name"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Generate a minimal HCL stub for the given resource type."""
    _import_cmd.config(
        resource_type=resource_type,
        resource_id=resource_id,
        tf_name=tf_name,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
