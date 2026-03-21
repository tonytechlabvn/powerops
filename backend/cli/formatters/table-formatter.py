"""Rich table formatters for TerraBot CLI output."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from backend.core import models

console = Console()


def templates_table(templates: list[models.Template], json_mode: bool = False) -> None:
    """Render a Rich table of available templates.

    Args:
        templates: List of Template objects to display.
        json_mode: If True, print raw JSON instead of table.
    """
    if json_mode:
        import json
        data = [
            {
                "name": t.metadata.name,
                "display_name": t.metadata.display_name,
                "provider": t.metadata.provider,
                "description": t.metadata.description,
                "version": t.metadata.version,
                "tags": t.metadata.tags,
            }
            for t in templates
        ]
        console.print_json(json.dumps(data))
        return

    table = Table(
        title="Available Templates",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        expand=False,
    )
    table.add_column("Name", style="bold green", no_wrap=True)
    table.add_column("Provider", style="magenta")
    table.add_column("Description", max_width=50)
    table.add_column("Tags", style="dim")
    table.add_column("Version", style="dim", justify="right")

    for tmpl in templates:
        table.add_row(
            tmpl.metadata.name,
            tmpl.metadata.provider,
            tmpl.metadata.description,
            ", ".join(tmpl.metadata.tags),
            tmpl.metadata.version,
        )

    console.print(table)


def template_info_panel(template: models.Template, json_mode: bool = False) -> None:
    """Render detailed info panel for a single template.

    Args:
        template: Template to display.
        json_mode: If True, print raw JSON instead of panel.
    """
    if json_mode:
        import json
        data = {
            "name": template.metadata.name,
            "display_name": template.metadata.display_name,
            "provider": template.metadata.provider,
            "description": template.metadata.description,
            "version": template.metadata.version,
            "tags": template.metadata.tags,
            "author": template.metadata.author,
            "variables": [
                {
                    "name": v.name,
                    "type": v.type,
                    "description": v.description,
                    "default": v.default,
                    "required": v.required,
                }
                for v in template.variables
            ],
        }
        console.print_json(json.dumps(data))
        return

    # Build variables table
    var_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    var_table.add_column("Variable", style="bold yellow", no_wrap=True)
    var_table.add_column("Type", style="cyan")
    var_table.add_column("Required", justify="center")
    var_table.add_column("Default", style="dim")
    var_table.add_column("Description")

    for v in template.variables:
        required_str = "[red]yes[/red]" if v.required else "[green]no[/green]"
        default_str = str(v.default) if v.default is not None else "[dim]—[/dim]"
        var_table.add_row(v.name, v.type, required_str, default_str, v.description)

    meta = template.metadata
    header = (
        f"[bold green]{meta.display_name}[/bold green]  "
        f"[dim]v{meta.version}[/dim]  "
        f"[magenta]{meta.provider}[/magenta]"
    )
    tags_str = "  ".join(f"[dim cyan]{t}[/dim cyan]" for t in meta.tags)

    content = f"{header}\n\n{meta.description}\n\nTags: {tags_str}\n\n"
    console.print(Panel(content, title="Template Info", border_style="cyan"))
    console.print(var_table)
