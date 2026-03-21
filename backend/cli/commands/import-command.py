"""terrabot import — guided terraform import wizard.

Commands:
  terrabot import resource  — import a single resource
  terrabot import bulk      — import multiple resources from a JSON mapping file
  terrabot import config    — generate an HCL stub for a resource type
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def _load_wizard():
    import importlib.util as ilu
    import sys

    alias = "backend.core.import_wizard"
    if alias in sys.modules:
        return sys.modules[alias]
    core_dir = Path(__file__).parent.parent.parent / "core"
    spec = ilu.spec_from_file_location(alias, core_dir / "import-wizard.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def resource(
    resource_type: str = typer.Argument(..., help="Terraform resource type, e.g. aws_instance"),
    resource_id: str = typer.Argument(..., help="Provider resource ID, e.g. i-0abc123"),
    tf_address: str = typer.Argument(..., help="Terraform address, e.g. aws_instance.web"),
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Import a single existing resource into Terraform state."""
    wizard = _load_wizard().ImportWizard()
    ws_dir = Path(working_dir).resolve()

    if not json_output:
        console.print(f"[bold cyan]Importing:[/bold cyan] {tf_address} ← {resource_id}")

    try:
        result = asyncio.run(
            wizard.run_import(
                resource_type=resource_type,
                resource_id=resource_id,
                tf_address=tf_address,
                workspace_dir=ws_dir,
            )
        )
    except Exception as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2))
        return

    if result["success"]:
        console.print(Panel(
            f"[green]Successfully imported[/green] [bold]{tf_address}[/bold]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red]Import failed:[/red] {result['error']}",
            border_style="red",
        ))
        raise typer.Exit(1)


def bulk(
    mapping_file: str = typer.Argument(..., help="JSON file with import mapping list"),
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Import multiple resources from a JSON mapping file.

    JSON format: [{"resource_type": "...", "resource_id": "...", "tf_address": "..."}]
    """
    mapping_path = Path(mapping_file).resolve()
    if not mapping_path.exists():
        console.print(f"[red]Mapping file not found:[/red] {mapping_path}")
        raise typer.Exit(1)

    try:
        mapping = json.loads(mapping_path.read_text())
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON in mapping file:[/red] {exc}")
        raise typer.Exit(1)

    wizard = _load_wizard().ImportWizard()
    ws_dir = Path(working_dir).resolve()

    if not json_output:
        console.print(f"[bold cyan]Bulk importing[/bold cyan] {len(mapping)} resource(s)...")

    try:
        results = asyncio.run(wizard.bulk_import(mapping=mapping, workspace_dir=ws_dir))
    except Exception as exc:
        console.print(f"[red]Bulk import failed:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(results, indent=2))
        return

    success_count = sum(1 for r in results if r["success"])
    for r in results:
        status = "[green]OK[/green]" if r["success"] else f"[red]FAIL[/red] {r['error']}"
        console.print(f"  {r['address']:<40} {status}")

    console.print(f"\n[bold]{success_count}/{len(results)} imported successfully.[/bold]")
    if success_count < len(results):
        raise typer.Exit(1)


def config(
    resource_type: str = typer.Argument(..., help="Terraform resource type, e.g. aws_instance"),
    resource_id: str = typer.Argument(..., help="Provider resource ID for reference"),
    tf_name: str = typer.Option("imported", "--name", "-n", help="Terraform logical resource name"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Generate a minimal HCL stub for the given resource type."""
    wizard = _load_wizard().ImportWizard()

    try:
        hcl = asyncio.run(
            wizard.generate_import_config(
                resource_type=resource_type,
                resource_id=resource_id,
                tf_name=tf_name,
            )
        )
    except Exception as exc:
        console.print(f"[red]Config generation failed:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps({"hcl": hcl}))
        return

    console.print(Syntax(hcl, "hcl", theme="monokai", line_numbers=False))
