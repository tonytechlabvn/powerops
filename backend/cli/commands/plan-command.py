"""terrabot plan — run terraform plan with Rich diff display."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()

import importlib.util as _ilu
from pathlib import Path as _Path

def _load_formatter(fname: str, alias: str):
    import sys
    full = f"backend.cli.formatters.{alias}"
    if full in sys.modules:
        return sys.modules[full]
    base = _Path(__file__).parent.parent / "formatters"
    spec = _ilu.spec_from_file_location(full, base / fname)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def run(
    working_dir: str = typer.Option(".", "--dir", "-d", help="Terraform working directory"),
    var_file: Optional[str] = typer.Option(None, "--var-file", help="Path to .tfvars file"),
    out: Optional[str] = typer.Option(None, "--out", help="Save plan binary to this path"),
    destroy: bool = typer.Option(False, "--destroy", help="Plan a destroy operation"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Run terraform plan and display a Rich diff of planned changes."""
    from backend.core import terraform_runner as tr_mod
    from backend.core.exceptions import TerraformError

    work_path = Path(working_dir).resolve()
    if not work_path.exists():
        console.print(f"[red]Working directory not found:[/red] {work_path}")
        raise typer.Exit(1)

    plan_fmt = _load_formatter("plan-formatter.py", "plan_formatter")
    progress_mod = _load_formatter("progress.py", "progress")  # reuse loader

    if not json_output:
        console.print(f"[bold cyan]Planning...[/bold cyan]  [dim]{work_path}[/dim]")

    try:
        runner = tr_mod.TerraformRunner(working_dir=work_path)
        with progress_mod.spinner("Running terraform plan"):
            result = asyncio.run(runner.plan(var_file=var_file, out=out, destroy=destroy))
    except TerraformError as exc:
        console.print(Panel(f"[red]Plan failed:[/red] {exc}", border_style="red"))
        if verbose and exc.stderr:
            console.print(exc.stderr)
        raise typer.Exit(1)

    plan_fmt.plan_summary(result, json_mode=json_output)
