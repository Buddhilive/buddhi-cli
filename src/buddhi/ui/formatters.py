"""Terminal presentation and formatted output helpers for BuddhiAI CLI."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _can_encode(char: str, console: Console) -> bool:
    """Check if the console's target encoding can encode the given character."""
    encoding = getattr(console.file, "encoding", None) or console.encoding
    if not encoding:
        return False
    try:
        char.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def get_symbols(console: Console) -> dict[str, str]:
    """Return symbols appropriate for the console's encoding capability."""
    if _can_encode("\u2713", console):
        return {
            "ok": "[bold green]\u2713[/bold green]",
            "warn": "[bold yellow]![/bold yellow]",
            "error": "[bold red]\u2717[/bold red]",
            "info": "[bold cyan]i[/bold cyan]",
            "bullet": "[dim]\u2022[/dim]",
            "arrow": "[cyan]\u2192[/cyan]",
        }
    return {
        "ok": "[bold green][done][/bold green]",
        "warn": "[bold yellow][!][/bold yellow]",
        "error": "[bold red][error][/bold red]",
        "info": "[bold cyan][info][/bold cyan]",
        "bullet": "[dim]*[/dim]",
        "arrow": "[cyan]->[/cyan]",
    }


def print_status(
    message: str,
    status: str = "ok",
    console: Console | None = None,
) -> None:
    """Print a styled status line with standardized icons."""
    target = console if console is not None else Console()
    symbols = get_symbols(target)
    icon = symbols.get(status, " ")
    target.print(f" {icon} {message}")


def print_init_summary(
    root: Path,
    graph_nodes: int,
    graph_edges: int,
    graph_communities: int,
    docs_total: int,
    docs_stale: int,
    harness_added: int,
    harness_existing: int,
    artifacts: Sequence[Path],
    migration_notices: Sequence[str] | None = None,
    console: Console | None = None,
) -> None:
    """Render a beautifully structured, developer-friendly summary for `buddhi init`."""
    target = console if console is not None else Console()
    symbols = get_symbols(target)

    # 1. Header status
    target.print(
        f"{symbols['ok']} [bold white]Initialized project:[/bold white] [cyan]{root}[/cyan]\n"
    )

    # 2. Overview Table / Metrics
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=False,
        pad_edge=False,
    )
    table.add_column("Component", style="bold", min_width=18)
    table.add_column("Status / Metrics", style="green")

    table.add_row(
        "Code Graph",
        f"{graph_nodes:,} nodes, {graph_edges:,} edges, {graph_communities} communities",
    )
    table.add_row(
        "Documentation Plan",
        f"{docs_total:,} concepts ({docs_stale} need generation)",
    )
    table.add_row(
        "Agent Harness",
        f"{harness_added} file(s) added, {harness_existing} existing preserved",
    )

    target.print(table)
    target.print()

    # 3. Migration / Modernization notices
    if migration_notices:
        target.print("[bold yellow]Modernization & Migrations:[/bold yellow]")
        for notice in migration_notices:
            target.print(f"  {symbols['arrow']} {notice}")
        target.print()

    # 4. Artifacts generated
    target.print("[bold cyan]Generated Artifacts:[/bold cyan]")
    for path in artifacts:
        try:
            rel_path = path.relative_to(root)
            display_path = str(rel_path)
        except (ValueError, RuntimeError):
            display_path = str(path)
        target.print(f"  {symbols['bullet']} [green]{display_path}[/green]")
    target.print()

    # 5. Next Steps Callout Panel
    next_step_text = Text()
    next_step_text.append("Open this codebase in ", style="white")
    next_step_text.append("Google Antigravity", style="bold cyan")
    next_step_text.append(" and run:\n", style="white")
    next_step_text.append("  1. ", style="dim")
    next_step_text.append("/document-codebase", style="bold yellow")
    next_step_text.append(
        " - generate comprehensive OKF codebase documentation\n", style="dim"
    )
    next_step_text.append("  2. ", style="dim")
    next_step_text.append("/specify", style="bold yellow")
    next_step_text.append(
        "           - start a feature specification in the SDD lifecycle", style="dim"
    )

    target.print(
        Panel(
            next_step_text,
            title="[bold green]Next Steps[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )
