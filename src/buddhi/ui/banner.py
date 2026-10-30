"""ASCII art banner and visual branding for BuddhiAI CLI."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

ASCII_ART_BANNER = r"""  ____            _     _ _     _      _    ___    ____ _     ___ 
 | __ ) _   _  __| | __| | |__ (_)    / \  |_ _|  / ___| |   |_ _|
 |  _ \| | | |/ _` |/ _` | '_ \| |   / _ \  | |  | |   | |    | | 
 | |_) | |_| | (_| | (_| | | | | |  / ___ \ | |  | |___| |___ | | 
 |____/ \__,_|\__,_|\__,_|_| |_|_| /_/   \_\___|  \____|_____|___|"""


def get_version(version: str | None = None) -> str:
    """Resolve CLI version string."""
    if version:
        return version
    try:
        from buddhi import __version__

        return __version__
    except (ImportError, AttributeError):
        return "1.0.0"


def render_banner(console: Console, version: str | None = None) -> None:
    """Render the BuddhiAI CLI banner to a Rich console.

    Degrades gracefully:
    - If console width < 70 columns or not a terminal: prints a compact styled header.
    - Otherwise: prints the full ASCII art in cyan followed by metadata and version.
    """
    resolved_version = get_version(version)
    width = console.width if console.width is not None else 80

    if width < 70:
        # Compact single-line fallback for narrow terminals
        title = Text()
        title.append("BuddhiAI CLI ", style="bold cyan")
        title.append(f"v{resolved_version}", style="bold green")
        title.append(" - Tree-Sitter Code Graph & Agent Harness", style="dim")
        console.print(title)
        console.print()
        return

    # Wide terminal: Full ASCII art
    console.print(ASCII_ART_BANNER, style="bold cyan")
    sub = Text()
    sub.append("BuddhiAI CLI", style="bold cyan")
    sub.append(" | ", style="dim")
    sub.append("Tree-Sitter Code Graph & Antigravity Agent Harness", style="cyan")
    sub.append(" | ", style="dim")
    sub.append(f"v{resolved_version}", style="bold green")
    console.print(sub)
    console.print()


def print_banner(version: str | None = None, console: Console | None = None) -> None:
    """Convenience helper to print banner using standard or provided console."""
    target_console = console if console is not None else Console()
    render_banner(target_console, version=version)
