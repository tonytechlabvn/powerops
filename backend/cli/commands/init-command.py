"""terrabot init — interactive project wizard command."""
from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

# Lazy-load kebab-case core modules via the __init__ loader
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

def _load_core(filename: str, alias: str):
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    core_dir = _Path(__file__).parent.parent.parent / "core"
    spec = _ilu.spec_from_file_location(full_name, core_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_PROVIDERS = {"aws": "Amazon Web Services", "proxmox": "Proxmox VE"}

_PROVIDER_CREDS: dict[str, list[tuple[str, str]]] = {
    "aws": [
        ("AWS_ACCESS_KEY_ID", "AWS Access Key ID"),
        ("AWS_SECRET_ACCESS_KEY", "AWS Secret Access Key"),
        ("AWS_DEFAULT_REGION", "Default region (e.g. us-east-1)"),
    ],
    "proxmox": [
        ("PROXMOX_VE_ENDPOINT", "Proxmox API URL (e.g. https://pve:8006/api2/json)"),
        ("PROXMOX_VE_USERNAME", "Proxmox username (e.g. root@pam)"),
        ("PROXMOX_VE_PASSWORD", "Proxmox password"),
    ],
}


def _write_toml(path: Path, provider: str, workspace: str) -> None:
    """Write .terrabot.toml project config file."""
    content = (
        f'# TerraBot project configuration\n'
        f'[project]\n'
        f'provider = "{provider}"\n'
        f'workspace = "{workspace}"\n\n'
        f'[terraform]\n'
        f'binary = "terraform"\n'
        f'timeout_seconds = 1800\n'
    )
    path.write_text(content, encoding="utf-8")


def run(
    workspace: str = typer.Option("./workspaces", "--workspace", "-w", help="Workspace directory"),
    provider: str = typer.Option("", "--provider", "-p", help="Provider: aws or proxmox"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug output"),
) -> None:
    """Interactive project initialisation wizard.

    Selects provider, validates credentials, and writes .terrabot.toml.
    """
    console.print(Panel("[bold cyan]TerraBot Init Wizard[/bold cyan]", expand=False))

    # Provider selection
    if not provider:
        console.print("\nAvailable providers:")
        for key, label in _PROVIDERS.items():
            console.print(f"  [bold]{key}[/bold] — {label}")
        provider = Prompt.ask(
            "\nSelect provider",
            choices=list(_PROVIDERS.keys()),
            default="aws",
        )

    if provider not in _PROVIDERS:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        raise typer.Exit(1)

    console.print(f"\nConfiguring for [bold magenta]{_PROVIDERS[provider]}[/bold magenta]")

    # Credential prompts
    import os
    creds_set = []
    for env_var, label in _PROVIDER_CREDS[provider]:
        existing = os.environ.get(env_var, "")
        if existing:
            console.print(f"  [dim]{env_var}[/dim] already set in environment — [green]OK[/green]")
            creds_set.append(env_var)
        else:
            value = Prompt.ask(f"  {label}", password="KEY" in env_var or "PASSWORD" in env_var)
            if value:
                os.environ[env_var] = value
                creds_set.append(env_var)

    # Write project config
    config_path = Path(".terrabot.toml")
    _write_toml(config_path, provider, workspace)
    console.print(f"\n[green]✓[/green] Wrote project config → [bold]{config_path}[/bold]")

    # Create workspace directory
    ws_path = Path(workspace)
    ws_path.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Workspace directory ready → [bold]{ws_path}[/bold]")

    if json_output:
        import json
        console.print_json(json.dumps({
            "provider": provider,
            "workspace": workspace,
            "config_file": str(config_path),
            "credentials_configured": creds_set,
        }))
    else:
        console.print(Panel(
            f"[green]Initialisation complete![/green]\n"
            f"Provider: [bold]{provider}[/bold]\n"
            f"Run [bold cyan]terrabot template list[/bold cyan] to browse available templates.",
            border_style="green",
        ))
