"""terrabot explain — stub for Phase 6 AI learning mode."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def run(
    term: str = typer.Argument(..., help="Terraform term or concept to explain"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Explain a Terraform concept using AI (coming in Phase 6 — learning mode)."""
    if json_output:
        import json
        console.print_json(json.dumps({
            "term": term,
            "status": "not_implemented",
            "message": "Coming soon in learning mode (Phase 6).",
        }))
        return

    console.print(Panel(
        f"[bold yellow]Coming soon in learning mode![/bold yellow]\n\n"
        f"The [bold cyan]explain[/bold cyan] command will use AI to explain "
        f"[bold green]{term}[/bold green] in Phase 6.\n\n"
        "[dim]Stay tuned for interactive Terraform learning with contextual examples.[/dim]",
        title="[dim]terrabot explain[/dim]",
        border_style="yellow",
    ))
