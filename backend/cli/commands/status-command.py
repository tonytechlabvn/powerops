"""terrabot status — show current workspace info and terraform state."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def run(
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Display current workspace status and terraform state summary."""
    from backend.core import terraform_runner as tr_mod
    from backend.core.exceptions import TerraformError

    work_path = Path(working_dir).resolve()

    # Read project config if present
    config_file = Path(".terrabot.toml")
    config_data: dict = {}
    if config_file.exists():
        try:
            import tomllib  # Python 3.11+
            with open(config_file, "rb") as fh:
                config_data = tomllib.load(fh)
        except Exception:
            pass

    # Gather workspace facts
    tf_files = list(work_path.glob("*.tf")) if work_path.exists() else []
    has_state = (work_path / "terraform.tfstate").exists()
    has_lock = (work_path / ".terraform.lock.hcl").exists()

    provider = config_data.get("project", {}).get("provider", "[dim]unknown[/dim]")

    if json_output:
        info: dict = {
            "working_dir": str(work_path),
            "provider": provider,
            "tf_files": len(tf_files),
            "has_state": has_state,
            "has_lock": has_lock,
        }
        # Attempt terraform output
        if work_path.exists() and tf_files:
            try:
                runner = tr_mod.TerraformRunner(working_dir=work_path)
                outputs = asyncio.run(runner.output())
                info["outputs"] = outputs
            except Exception:
                info["outputs"] = {}
        console.print_json(json.dumps(info))
        return

    # Rich panel display
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold dim", no_wrap=True)
    table.add_column("Value")

    table.add_row("Working Dir", str(work_path))
    table.add_row("Provider", str(provider))
    table.add_row("Terraform files", str(len(tf_files)))
    table.add_row("State file", "[green]present[/green]" if has_state else "[dim]none[/dim]")
    table.add_row("Lock file", "[green]present[/green]" if has_lock else "[dim]none[/dim]")

    console.print(Panel(table, title="[bold cyan]Workspace Status[/bold cyan]", border_style="cyan"))

    # Attempt terraform output for additional context
    if work_path.exists() and tf_files:
        try:
            runner = tr_mod.TerraformRunner(working_dir=work_path)
            outputs = asyncio.run(runner.output())
            if outputs:
                out_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                out_table.add_column("Output", style="yellow")
                out_table.add_column("Value")
                for key, val in outputs.items():
                    value = val.get("value", val) if isinstance(val, dict) else val
                    out_table.add_row(key, str(value))
                console.print("\n[bold]Terraform Outputs[/bold]")
                console.print(out_table)
        except TerraformError:
            if verbose:
                console.print("[dim]No terraform outputs available (run init + apply first).[/dim]")
