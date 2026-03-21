"""terrabot template — list, use, and info sub-commands."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

# ---------------------------------------------------------------------------
# Lazy core loader (mirrors pattern in core/__init__.py)
# ---------------------------------------------------------------------------

import importlib.util as _ilu
from pathlib import Path as _Path

def _load_core(filename: str, alias: str):
    import sys as _sys
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    core_dir = _Path(__file__).parent.parent.parent / "core"
    spec = _ilu.spec_from_file_location(full_name, core_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _get_formatters():
    """Lazy-import CLI formatters (avoids circular at module load time)."""
    import importlib.util as ilu
    import sys
    base = _Path(__file__).parent.parent / "formatters"

    def _fmt(fname, alias):
        full = f"backend.cli.formatters.{alias}"
        if full in sys.modules:
            return sys.modules[full]
        spec = ilu.spec_from_file_location(full, base / fname)
        mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules[full] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    return (
        _fmt("table-formatter.py", "table_formatter"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt_missing_vars(template, provided: dict) -> dict:
    """Interactively prompt for any required variables not already supplied."""
    result = dict(provided)
    for var in template.variables:
        if var.name in result:
            continue
        if not var.required and var.default is not None:
            result[var.name] = var.default
            continue
        default_hint = f" [{var.default}]" if var.default is not None else ""
        value = Prompt.ask(
            f"  [yellow]{var.name}[/yellow] ({var.type}){default_hint} — {var.description}",
            default=str(var.default) if var.default is not None else "",
        )
        # Coerce simple types
        if var.type == "number":
            try:
                result[var.name] = float(value) if "." in value else int(value)
            except ValueError:
                result[var.name] = value
        elif var.type == "bool":
            result[var.name] = value.lower() in ("true", "1", "yes")
        else:
            result[var.name] = value
    return result


def _parse_var_args(var_pairs: list[str]) -> dict:
    """Parse key=value strings into a dict."""
    result = {}
    for pair in var_pairs:
        if "=" not in pair:
            console.print(f"[red]Invalid --var format (expected key=value): {pair}[/red]")
            raise typer.Exit(1)
        key, _, value = pair.partition("=")
        result[key.strip()] = value.strip()
    return result


# ---------------------------------------------------------------------------
# Sub-command implementations (called from main.py)
# ---------------------------------------------------------------------------

def list_templates(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider: aws or proxmox"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """List all available TerraBot templates."""
    from backend.core import template_engine

    templates = template_engine.list_templates(provider=provider)

    if not templates:
        msg = f"No templates found" + (f" for provider '{provider}'" if provider else "")
        console.print(f"[yellow]{msg}[/yellow]")
        return

    (table_fmt,) = _get_formatters()
    table_fmt.templates_table(templates, json_mode=json_output)

    if not json_output:
        console.print(
            f"\n[dim]Found {len(templates)} template(s). "
            f"Use [bold]terrabot template info <name>[/bold] for details.[/dim]"
        )


def use_template(
    name: str = typer.Argument(..., help="Template name, e.g. aws/ec2-web-server"),
    var: list[str] = typer.Option([], "--var", help="Variable overrides: key=value (repeatable)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write rendered HCL to this file"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Render a template to HCL, prompting interactively for missing variables."""
    from backend.core import template_engine
    from backend.core.exceptions import TemplateError, ValidationError

    try:
        template = template_engine.get_template(name)
    except TemplateError as exc:
        console.print(f"[red]Template not found:[/red] {exc}")
        raise typer.Exit(1)

    if not json_output:
        (table_fmt,) = _get_formatters()
        table_fmt.template_info_panel(template)
        console.print("\n[bold]Configuring variables...[/bold]")

    provided = _parse_var_args(var)
    variables = _prompt_missing_vars(template, provided)

    try:
        hcl = template_engine.render_template(name, variables)
    except ValidationError as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        for v in exc.violations:
            console.print(f"  [red]•[/red] {v}")
        raise typer.Exit(1)
    except TemplateError as exc:
        console.print(f"[red]Render error:[/red] {exc}")
        raise typer.Exit(1)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(hcl, encoding="utf-8")
        if json_output:
            console.print_json(json.dumps({"output_file": str(out_path), "template": name}))
        else:
            console.print(f"\n[green]✓[/green] Rendered HCL written to [bold]{out_path}[/bold]")
    else:
        if json_output:
            console.print_json(json.dumps({"hcl": hcl, "template": name}))
        else:
            console.print(Panel(hcl, title=f"[green]{name}[/green]", border_style="dim"))


def template_info(
    name: str = typer.Argument(..., help="Template name, e.g. aws/ec2-web-server"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Show detailed information about a specific template."""
    from backend.core import template_engine
    from backend.core.exceptions import TemplateError

    try:
        template = template_engine.get_template(name)
    except TemplateError as exc:
        console.print(f"[red]Template not found:[/red] {exc}")
        raise typer.Exit(1)

    (table_fmt,) = _get_formatters()
    table_fmt.template_info_panel(template, json_mode=json_output)
