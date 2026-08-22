from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from buddhi.docgen.planner import build_docs_plan, plan_to_json
from buddhi.graph.pipeline import run_pipeline
from buddhi.util.fsutil import BuddhiFsError, ensure_buddhi_dirs, ensure_docs_dir

console = Console()
err_console = Console(stderr=True)

docs_app = typer.Typer(help="Documentation planning for the current code graph.")


@docs_app.command(name="plan")
def plan(
    path: Path = typer.Argument(Path("."), help="Root directory to scan."),  # noqa: B008
    max_file_size: int = typer.Option(
        2_000_000, "--max-file-size", help="Skip files larger than this, in bytes."
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Print per-file warnings."),
) -> None:
    """Compute a bottom-up, staleness-aware doc-generation plan and write docs-plan.json."""
    root = path.resolve()

    if not root.exists():
        err_console.print(f"[red]error:[/red] path does not exist: {root}")
        raise typer.Exit(code=1)
    if not root.is_dir():
        err_console.print(f"[red]error:[/red] not a directory: {root}")
        raise typer.Exit(code=1)

    try:
        ensure_buddhi_dirs(root)
        ensure_docs_dir(root)
    except BuddhiFsError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    result = run_pipeline(root, max_file_size=max_file_size)
    if verbose:
        for warning in result.build_ctx.warnings:
            err_console.print(f"[yellow]warning:[/yellow] {warning}")

    entries = build_docs_plan(result.build_ctx.graph, root)
    plan_path = root / ".buddhi" / "docs-plan.json"
    try:
        plan_path.write_text(json.dumps(plan_to_json(entries), indent=2), encoding="utf-8")
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing {plan_path}: {exc}")
        raise typer.Exit(code=1) from exc

    stale = sum(1 for e in entries if e.needs_generation)
    console.print(f"[bold green]done[/bold green] planned docs for {root}")
    console.print(f"  entries: {len(entries)} total, {stale} need (re)generation")
    console.print(f"  wrote: {plan_path}")
