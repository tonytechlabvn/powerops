"""Rich progress bars and spinners for long-running terraform operations."""
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

console = Console()


@contextmanager
def spinner(message: str) -> Generator[None, None, None]:
    """Context manager displaying a spinner with a status message.

    Args:
        message: Text shown next to the spinner.

    Yields:
        None — caller executes inside the context.
    """
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        yield


@contextmanager
def operation_progress(title: str) -> Generator[Progress, None, None]:
    """Context manager providing a Rich Progress instance for multi-step ops.

    Args:
        title: Label shown above the progress bar.

    Yields:
        Progress instance the caller can add tasks to.
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    console.print(f"\n[bold]{title}[/bold]")
    with progress:
        yield progress


def print_step(step: str, status: str = "ok") -> None:
    """Print a single labeled step result.

    Args:
        step: Step description.
        status: 'ok' (green check), 'fail' (red x), or 'skip' (dim dash).
    """
    icons = {"ok": "[green]✓[/green]", "fail": "[red]✗[/red]", "skip": "[dim]–[/dim]"}
    icon = icons.get(status, "[dim]?[/dim]")
    console.print(f"  {icon}  {step}")
