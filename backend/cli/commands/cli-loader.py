"""Utility to load kebab-case command modules for the CLI."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_COMMANDS_DIR = Path(__file__).parent


def load_command(filename: str, alias: str):
    """Load a kebab-case command module and register it under backend.cli.commands.<alias>.

    Idempotent — returns cached module if already loaded.

    Args:
        filename: Kebab-case filename, e.g. "init-command.py".
        alias: Snake_case alias, e.g. "init_command".

    Returns:
        Loaded module object.
    """
    full_name = f"backend.cli.commands.{alias}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    spec = importlib.util.spec_from_file_location(full_name, _COMMANDS_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate command module: {filename}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def load_formatter(filename: str, alias: str):
    """Load a kebab-case formatter module and register it under backend.cli.formatters.<alias>.

    Args:
        filename: Kebab-case filename, e.g. "plan-formatter.py".
        alias: Snake_case alias, e.g. "plan_formatter".

    Returns:
        Loaded module object.
    """
    full_name = f"backend.cli.formatters.{alias}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    formatters_dir = _COMMANDS_DIR.parent / "formatters"
    spec = importlib.util.spec_from_file_location(full_name, formatters_dir / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate formatter module: {filename}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod
