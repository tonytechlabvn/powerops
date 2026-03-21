"""terrabot destroy — double confirmation then destroy with progress."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

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
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip confirmation prompts"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Destroy all terraform-managed infrastructure (requires double confirmation)."""
    from backend.core import terraform_runner as tr_mod
    from backend.core.exceptions import TerraformError

    work_path = Path(working_dir).resolve()
    if not work_path.exists():
        console.print(f"[red]Working directory not found:[/red] {work_path}")
        raise typer.Exit(1)

    plan_fmt = _load_formatter("plan-formatter.py", "plan_formatter")
    progress_mod = _load_formatter("progress.py", "progress_mod")

    if not auto_approve and not json_output:
        console.print(Panel(
            "[bold red]WARNING: This will DESTROY all terraform-managed infrastructure.[/bold red]\n"
            "This action cannot be undone.",
            border_style="red",
            title="Destructive Operation",
        ))
        # First confirmation
        if not Confirm.ask("[red]Are you sure you want to destroy?[/red]", default=False):
            console.print("[dim]Destroy cancelled.[/dim]")
            raise typer.Exit(0)

        # Second confirmation — type workspace name
        confirm_word = Prompt.ask(
            '[yellow]Type "[bold]destroy[/bold]" to confirm[/yellow]'
        )
        if confirm_word.strip().lower() != "destroy":
            console.print("[dim]Confirmation word did not match. Destroy cancelled.[/dim]")
            raise typer.Exit(0)

    if not json_output:
        console.print(f"[bold red]Destroying...[/bold red]  [dim]{work_path}[/dim]")

    try:
        runner = tr_mod.TerraformRunner(working_dir=work_path)
        with progress_mod.spinner("Running terraform destroy"):
            result = asyncio.run(runner.destroy(auto_approve=True, var_file=var_file))
    except TerraformError as exc:
        console.print(Panel(f"[red]Destroy failed:[/red] {exc}", border_style="red"))
        if verbose and exc.stderr:
            console.print(exc.stderr)
        raise typer.Exit(1)

    plan_fmt.destroy_summary(result, json_mode=json_output)
