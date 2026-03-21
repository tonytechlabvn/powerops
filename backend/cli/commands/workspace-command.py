"""terrabot workspace — multi-workspace lifecycle management.

Commands:
  terrabot workspace create  — create a new workspace
  terrabot workspace list    — list all workspaces
  terrabot workspace switch  — switch active workspace
  terrabot workspace delete  — delete a workspace
  terrabot workspace current — show current workspace
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def _load_manager():
    import importlib.util as ilu
    import sys

    alias = "backend.core.workspace_manager"
    if alias in sys.modules:
        return sys.modules[alias]
    core_dir = Path(__file__).parent.parent.parent / "core"
    spec = ilu.spec_from_file_location(alias, core_dir / "workspace-manager.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _mgr():
    from backend.core.config import get_settings
    mod = _load_manager()
    return mod.WorkspaceManager(base_dir=get_settings().working_dir)


def create(
    name: str = typer.Argument(..., help="Workspace name"),
    provider: str = typer.Option("", "--provider", "-p", help="Cloud provider (aws, proxmox, etc.)"),
    environment: str = typer.Option("", "--env", "-e", help="Environment label (dev, staging, prod)"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Create a new Terraform workspace."""
    try:
        result = asyncio.run(_mgr().create(name=name, provider=provider, environment=environment))
    except Exception as exc:
        console.print(f"[red]Failed to create workspace:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2))
        return

    console.print(f"[green]Workspace created:[/green] {result['name']}")
    console.print(f"  Directory : {result['workspace_dir']}")
    if result.get("provider"):
        console.print(f"  Provider  : {result['provider']}")
    if result.get("environment"):
        console.print(f"  Env       : {result['environment']}")


def list_workspaces(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """List all registered workspaces."""
    try:
        items = asyncio.run(_mgr().list_workspaces())
    except Exception as exc:
        console.print(f"[red]Failed to list workspaces:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(items, indent=2))
        return

    if not items:
        console.print("[dim]No workspaces found.[/dim]")
        return

    table = Table(title="Workspaces", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Provider")
    table.add_column("Environment")
    table.add_column("Last Used", style="dim")
    for w in items:
        table.add_row(
            w.get("name", ""),
            w.get("provider", "—"),
            w.get("environment", "—"),
            (w.get("last_used") or "—")[:19],
        )
    console.print(table)


def switch(
    name: str = typer.Argument(..., help="Workspace name to switch to"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Switch the active Terraform workspace."""
    try:
        result = asyncio.run(_mgr().switch(name))
    except Exception as exc:
        console.print(f"[red]Failed to switch workspace:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2))
        return

    console.print(f"[green]Switched to workspace:[/green] {name}")


def delete(
    name: str = typer.Argument(..., help="Workspace name to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Delete a workspace and its directory."""
    if not yes:
        confirmed = typer.confirm(f"Delete workspace '{name}' and all its files?", default=False)
        if not confirmed:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    try:
        asyncio.run(_mgr().delete(name))
    except Exception as exc:
        console.print(f"[red]Failed to delete workspace:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps({"deleted": name}))
        return

    console.print(f"[green]Workspace deleted:[/green] {name}")


def current(
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Show the currently active workspace."""
    try:
        result = asyncio.run(_mgr().get_current())
    except Exception as exc:
        console.print(f"[red]Failed to get current workspace:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2))
        return

    console.print(f"[bold cyan]Current workspace:[/bold cyan] {result.get('name', 'default')}")
    if result.get("provider"):
        console.print(f"  Provider : {result['provider']}")
    if result.get("environment"):
        console.print(f"  Env      : {result['environment']}")
