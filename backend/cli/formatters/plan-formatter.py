"""Rich plan diff display for terraform plan output."""
from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from backend.core import models

console = Console()

# Action → (symbol, color)
_ACTION_STYLE: dict[str, tuple[str, str]] = {
    "create": ("+", "green"),
    "update": ("~", "yellow"),
    "delete": ("-", "red"),
    "replace": ("±", "magenta"),
    "no-op": ("=", "dim"),
    "read": ("»", "cyan"),
}


def plan_summary(result: models.PlanResult, json_mode: bool = False) -> None:
    """Render terraform plan results with a Rich diff-style table.

    Args:
        result: PlanResult from TerraformRunner.plan().
        json_mode: If True, print raw JSON instead of rich output.
    """
    if json_mode:
        data = {
            "success": result.success,
            "terraform_version": result.terraform_version,
            "resource_changes": [
                {
                    "address": rc.address,
                    "type": rc.type,
                    "action": rc.action,
                }
                for rc in result.resource_changes
            ],
        }
        console.print_json(json.dumps(data))
        return

    changes = result.resource_changes
    if not changes:
        console.print(Panel("[green]No changes.[/green] Infrastructure is up-to-date.", border_style="green"))
        return

    table = Table(
        title="Planned Changes",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        expand=False,
    )
    table.add_column("Action", justify="center", width=6)
    table.add_column("Resource Address", style="bold")
    table.add_column("Type", style="dim")

    counts: dict[str, int] = {}
    for rc in changes:
        action_key = rc.action.value if hasattr(rc.action, "value") else str(rc.action)
        symbol, color = _ACTION_STYLE.get(action_key, ("?", "white"))
        table.add_row(
            f"[{color}]{symbol}[/{color}]",
            rc.address,
            rc.type,
        )
        counts[action_key] = counts.get(action_key, 0) + 1

    console.print(table)

    # Summary line
    parts = []
    for action, count in counts.items():
        sym, col = _ACTION_STYLE.get(action, ("?", "white"))
        parts.append(f"[{col}]{count} to {action}[/{col}]")
    console.print("  " + "  |  ".join(parts))


def apply_summary(result: models.ApplyResult, json_mode: bool = False) -> None:
    """Render apply result summary.

    Args:
        result: ApplyResult from TerraformRunner.apply().
        json_mode: If True, print raw JSON.
    """
    if json_mode:
        console.print_json(json.dumps({"success": result.success, "outputs": result.outputs}))
        return

    if result.success:
        console.print(Panel("[green]Apply complete![/green]", border_style="green"))
    else:
        console.print(Panel("[red]Apply failed.[/red]", border_style="red"))

    if result.outputs:
        out_table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        out_table.add_column("Output", style="bold yellow")
        out_table.add_column("Value")
        for key, val in result.outputs.items():
            value = val.get("value", val) if isinstance(val, dict) else val
            out_table.add_row(key, str(value))
        console.print(out_table)


def destroy_summary(result: models.DestroyResult, json_mode: bool = False) -> None:
    """Render destroy result summary."""
    if json_mode:
        console.print_json(
            json.dumps({"success": result.success, "resources_destroyed": result.resources_destroyed})
        )
        return

    color = "green" if result.success else "red"
    msg = (
        f"[{color}]Destroy complete![/{color}] "
        f"[dim]{result.resources_destroyed} resource(s) destroyed.[/dim]"
    )
    console.print(Panel(msg, border_style=color))
