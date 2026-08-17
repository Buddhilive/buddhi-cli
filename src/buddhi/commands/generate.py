from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from buddhi.discovery.walker import walk
from buddhi.graph.builder import build_graph
from buddhi.graph.resolver import resolve
from buddhi.languages.registry import available_languages
from buddhi.persist.html_writer import write_html
from buddhi.persist.json_writer import write_json
from buddhi.persist.sqlite_writer import write_sqlite
from buddhi.util.fsutil import BuddhiFsError, ensure_buddhi_dirs

console = Console()
err_console = Console(stderr=True)


def generate(
    path: Path = typer.Argument(Path("."), help="Root directory to scan."),  # noqa: B008
    tree: bool = typer.Option(
        True,
        "--tree/--no-tree",
        help="Reserved for interface stability; graph generation is always full "
        "(JSON + SQLite + HTML are always produced).",
    ),
    max_file_size: int = typer.Option(
        2_000_000, "--max-file-size", help="Skip files larger than this, in bytes."
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Print per-file warnings."),
) -> None:
    """Scan PATH, build a code graph, and write it to .buddhi/graphs/."""
    root = path.resolve()

    if not root.exists():
        err_console.print(f"[red]error:[/red] path does not exist: {root}")
        raise typer.Exit(code=1)
    if not root.is_dir():
        err_console.print(f"[red]error:[/red] not a directory: {root}")
        raise typer.Exit(code=1)

    lang_status = available_languages()
    avail = {lang for lang, err in lang_status.items() if err is None}
    if verbose:
        for lang, err in lang_status.items():
            if err is not None:
                err_console.print(f"[yellow]warning:[/yellow] language '{lang}' unavailable: {err}")

    walk_result = walk(root, max_file_size=max_file_size, available_languages=avail)

    if not walk_result.files:
        console.print("[yellow]warning:[/yellow] no supported source files found under this path.")

    build_ctx = build_graph(walk_result)
    resolve(build_ctx)

    if verbose:
        for warning in build_ctx.warnings:
            err_console.print(f"[yellow]warning:[/yellow] {warning}")

    try:
        graphs_dir = ensure_buddhi_dirs(root)
    except BuddhiFsError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    json_path = graphs_dir / "tree-graph.json"
    db_path = graphs_dir / "tree-graph.db"
    html_path = graphs_dir / "tree-graph.html"

    try:
        write_json(build_ctx.graph, json_path)
        write_sqlite(build_ctx.graph, db_path, root_path=str(root))
        write_html(build_ctx.graph, html_path, root_label=root.name or str(root))
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing artifacts: {exc}")
        raise typer.Exit(code=1) from exc

    languages_seen = sorted({f.language for f in walk_result.files})
    console.print(f"[bold green]done[/bold green] scanned {root}")
    console.print(
        f"  files: {build_ctx.stats.get('files_parsed', 0)} parsed, "
        f"{build_ctx.stats.get('files_failed', 0)} failed, "
        f"{len(walk_result.skipped_too_large)} skipped (too large)"
    )
    console.print(f"  languages: {', '.join(languages_seen) if languages_seen else '(none)'}")
    console.print(
        f"  graph: {len(build_ctx.graph.nodes)} nodes, {len(build_ctx.graph.edges)} edges"
    )
    console.print(f"  wrote: {json_path}")
    console.print(f"  wrote: {db_path}")
    console.print(f"  wrote: {html_path}")

    if walk_result.skipped_unsupported_grammar:
        for lang, count in walk_result.skipped_unsupported_grammar.items():
            console.print(
                f"  [yellow]skipped {count} .{lang} file(s): grammar unavailable[/yellow]"
            )
