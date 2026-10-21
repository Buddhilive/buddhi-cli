from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from buddhi.docgen.planner import build_docs_plan, plan_to_json
from buddhi.docgen.site import compile_site, serve_docs
from buddhi.graph.pipeline import run_pipeline
from buddhi.util.fsutil import (
    BuddhiFsError,
    ensure_buddhi_dirs,
    ensure_docs_dir,
    ensure_site_dir,
)

console = Console()
err_console = Console(stderr=True)

docs_app = typer.Typer(
    help="Pelican static site and live documentation for OKF v0.2 and code graph.",
    invoke_without_command=True,
)


def _prepare_directories_and_graph(
    root: Path,
    no_graph_refresh: bool = False,
    max_file_size: int = 2_000_000,
    verbose: bool = False,
) -> None:
    """Ensure .buddhi dirs exist and graph is initialized."""
    try:
        ensure_buddhi_dirs(root)
        ensure_docs_dir(root)
        ensure_site_dir(root)
    except BuddhiFsError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    db_path = root / ".buddhi" / "graphs" / "tree-graph.db"
    if not no_graph_refresh or not db_path.exists():
        result = run_pipeline(root, max_file_size=max_file_size)
        if verbose:
            for warning in result.build_ctx.warnings:
                err_console.print(f"[yellow]warning:[/yellow] {warning}")


def _run_docs_serve(
    path: Path,
    port: int,
    host: str,
    reload: bool,
    open_browser: bool,
    no_graph_refresh: bool,
    output: Path | None,
    verbose: bool,
) -> None:
    root = path.resolve()
    if not root.is_dir():
        err_console.print(f"[red]error:[/red] not a directory: {root}")
        raise typer.Exit(code=1)

    _prepare_directories_and_graph(
        root, no_graph_refresh=no_graph_refresh, verbose=verbose
    )

    try:
        serve_docs(
            root=root,
            host=host,
            port=port,
            reload=reload,
            open_browser=open_browser,
            output_dir=output,
            verbose=verbose,
        )
    except OSError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@docs_app.callback()
def default_docs_callback(
    ctx: typer.Context,
    port: int = typer.Option(8000, "--port", "-p", help="Server port."),
    host: str = typer.Option("127.0.0.1", "--host", help="Server bind host."),
    reload: bool = typer.Option(
        True, "--reload/--no-reload", help="Auto-reload on file changes."
    ),
    open_browser: bool = typer.Option(
        False, "--open/--no-open", help="Open browser on start."
    ),
    no_graph_refresh: bool = typer.Option(
        False, "--no-graph-refresh", help="Skip graph refresh check."
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Custom output directory."
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Print verbose warnings."
    ),
) -> None:
    """Run the live documentation site (default command)."""
    if ctx.invoked_subcommand is None:
        _run_docs_serve(
            path=Path("."),
            port=port,
            host=host,
            reload=reload,
            open_browser=open_browser,
            no_graph_refresh=no_graph_refresh,
            output=output,
            verbose=verbose,
        )


@docs_app.command(name="serve")
def serve_command(
    path: Path = typer.Argument(Path("."), help="Root directory to document."),  # noqa: B008
    port: int = typer.Option(8000, "--port", "-p", help="Server port."),
    host: str = typer.Option("127.0.0.1", "--host", help="Server bind host."),
    reload: bool = typer.Option(
        True, "--reload/--no-reload", help="Auto-reload on file changes."
    ),
    open_browser: bool = typer.Option(
        False, "--open/--no-open", help="Open browser on start."
    ),
    no_graph_refresh: bool = typer.Option(
        False, "--no-graph-refresh", help="Skip graph refresh check."
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Custom output directory."
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Print verbose warnings."
    ),
) -> None:
    """Serve the live documentation site with hot-reload."""
    _run_docs_serve(
        path=path,
        port=port,
        host=host,
        reload=reload,
        open_browser=open_browser,
        no_graph_refresh=no_graph_refresh,
        output=output,
        verbose=verbose,
    )


@docs_app.command(name="build")
def build_command(
    path: Path = typer.Argument(Path("."), help="Root directory to document."),  # noqa: B008
    no_graph_refresh: bool = typer.Option(
        False, "--no-graph-refresh", help="Skip graph refresh check."
    ),
    output: Path | None = typer.Option(  # noqa: B008
        None, "--output", "-o", help="Custom output directory."
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Print verbose warnings."
    ),
) -> None:
    """Compile the Pelican static documentation site into .buddhi/site/ without serving."""
    root = path.resolve()
    if not root.is_dir():
        err_console.print(f"[red]error:[/red] not a directory: {root}")
        raise typer.Exit(code=1)

    _prepare_directories_and_graph(
        root, no_graph_refresh=no_graph_refresh, verbose=verbose
    )

    try:
        out = compile_site(root=root, output_dir=output, verbose=verbose)
        console.print(
            f"[bold green]done[/bold green] compiled documentation site at {out}"
        )
    except Exception as exc:
        err_console.print(
            f"[red]error:[/red] failed compiling documentation site: {exc}"
        )
        raise typer.Exit(code=1) from exc


@docs_app.command(name="plan")
def plan(
    path: Path = typer.Argument(Path("."), help="Root directory to scan."),  # noqa: B008
    max_file_size: int = typer.Option(
        2_000_000, "--max-file-size", help="Skip files larger than this, in bytes."
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Print per-file warnings."
    ),
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
        ensure_site_dir(root)
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
        plan_path.write_text(
            json.dumps(plan_to_json(entries), indent=2), encoding="utf-8"
        )
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing {plan_path}: {exc}")
        raise typer.Exit(code=1) from exc

    stale = sum(1 for e in entries if e.needs_generation)
    console.print(f"[bold green]done[/bold green] planned docs for {root}")
    console.print(f"  entries: {len(entries)} total, {stale} need (re)generation")
    console.print(f"  wrote: {plan_path}")
