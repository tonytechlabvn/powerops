"""terrabot drift — detect and report infrastructure drift.

Commands:
  terrabot drift check    — run a drift check for a workspace directory
  terrabot drift history  — show past drift reports from the database
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _load_detector():
    import importlib.util as ilu
    import sys

    alias = "backend.core.drift_detector"
    if alias in sys.modules:
        return sys.modules[alias]
    core_dir = Path(__file__).parent.parent.parent / "core"
    spec = ilu.spec_from_file_location(alias, core_dir / "drift-detector.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def check(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Logical workspace name"),
    workspace_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Run a drift check against live infrastructure."""
    mod = _load_detector()
    detector = mod.DriftDetector()

    ws_dir = Path(workspace_dir).resolve()
    if not json_output:
        console.print(f"[bold cyan]Checking drift for workspace:[/bold cyan] {workspace}")

    try:
        report = asyncio.run(detector.check_drift(workspace=workspace, workspace_dir=ws_dir))
    except Exception as exc:
        console.print(f"[red]Drift check failed:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps({
            "workspace": report.workspace,
            "timestamp": report.timestamp,
            "has_drift": report.has_drift,
            "drifted_resources": report.drifted_resources,
            "error": report.error,
        }, indent=2))
        return

    if report.error:
        console.print(Panel(f"[red]Error:[/red] {report.error}", border_style="red"))
        raise typer.Exit(1)

    if not report.has_drift:
        console.print(Panel("[green]No drift detected.[/green] Infrastructure matches state.", border_style="green"))
        return

    table = Table(title=f"Drifted Resources — {workspace}", show_header=True)
    table.add_column("Address", style="yellow")
    table.add_column("Type", style="cyan")
    table.add_column("Actions", style="red")
    for r in report.drifted_resources:
        table.add_row(r.get("address", ""), r.get("type", ""), ", ".join(r.get("actions", [])))

    console.print(Panel(table, title="[bold red]Drift Detected[/bold red]", border_style="red"))


def history(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Logical workspace name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Show drift check history for a workspace."""
    mod = _load_detector()
    detector = mod.DriftDetector()

    try:
        records = asyncio.run(detector.get_drift_history(workspace=workspace, limit=limit))
    except Exception as exc:
        console.print(f"[red]Failed to fetch history:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps([
            {
                "workspace": r.workspace,
                "timestamp": r.timestamp,
                "has_drift": r.has_drift,
                "drifted_resources": r.drifted_resources,
            }
            for r in records
        ], indent=2))
        return

    if not records:
        console.print("[dim]No drift history found.[/dim]")
        return

    table = Table(title=f"Drift History — {workspace}", show_header=True)
    table.add_column("Timestamp", style="dim")
    table.add_column("Drift", style="bold")
    table.add_column("Resources")
    for r in records:
        status = "[red]YES[/red]" if r.has_drift else "[green]NO[/green]"
        count = str(len(r.drifted_resources))
        table.add_row(r.timestamp, status, count)

    console.print(table)
