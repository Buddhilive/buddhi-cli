from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import typer
from rich.console import Console

from buddhi.docgen.planner import build_docs_plan, plan_to_json
from buddhi.graph.pipeline import run_pipeline
from buddhi.persist.html_writer import write_html
from buddhi.persist.json_writer import write_json
from buddhi.persist.sqlite_writer import write_sqlite
from buddhi.util.fsutil import (
    BuddhiFsError,
    ensure_buddhi_dirs,
    ensure_docs_dir,
    sync_template_tree,
)

console = Console()
err_console = Console(stderr=True)

_AGENTS_TEMPLATE_PACKAGE = "buddhi.templates.agents"


def init(
    path: Path = typer.Argument(Path("."), help="Root directory to initialize."),  # noqa: B008
    max_file_size: int = typer.Option(
        2_000_000, "--max-file-size", help="Skip files larger than this, in bytes."
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Print per-file warnings."),
) -> None:
    """Build the code graph, plan docs, and scaffold a Google Antigravity agent harness.

    The harness covers doc generation plus a general full-stack planning layer
    (frontend/backend/database/testing/security/deployment/git specialist
    agents, orchestrated by the /plan workflow). Idempotent: rerunning never
    overwrites a harness file you've already created or edited under .agents/
    — it only fills in what's missing.
    """
    root = path.resolve()

    if not root.exists():
        err_console.print(f"[red]error:[/red] path does not exist: {root}")
        raise typer.Exit(code=1)
    if not root.is_dir():
        err_console.print(f"[red]error:[/red] not a directory: {root}")
        raise typer.Exit(code=1)

    result = run_pipeline(root, max_file_size=max_file_size)
    if verbose:
        for lang, err in result.language_warnings.items():
            err_console.print(f"[yellow]warning:[/yellow] language '{lang}' unavailable: {err}")
        for warning in result.build_ctx.warnings:
            err_console.print(f"[yellow]warning:[/yellow] {warning}")

    try:
        graphs_dir = ensure_buddhi_dirs(root)
        ensure_docs_dir(root)
    except BuddhiFsError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    json_path = graphs_dir / "tree-graph.json"
    db_path = graphs_dir / "tree-graph.db"
    html_path = graphs_dir / "tree-graph.html"

    try:
        write_json(result.build_ctx.graph, json_path)
        write_sqlite(result.build_ctx.graph, db_path, root_path=str(root))
        write_html(result.build_ctx.graph, html_path, root_label=root.name or str(root))
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing graph artifacts: {exc}")
        raise typer.Exit(code=1) from exc

    plan_entries = build_docs_plan(result.build_ctx.graph, root)
    plan_path = root / ".buddhi" / "docs-plan.json"
    try:
        plan_path.write_text(json.dumps(plan_to_json(plan_entries), indent=2), encoding="utf-8")
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing {plan_path}: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        template_root = resources.files(_AGENTS_TEMPLATE_PACKAGE)
        with resources.as_file(template_root) as template_dir:
            sync_report = sync_template_tree(template_dir, root / ".agents")
    except (BuddhiFsError, ModuleNotFoundError, FileNotFoundError) as exc:
        err_console.print(f"[red]error:[/red] failed scaffolding .agents/: {exc}")
        raise typer.Exit(code=1) from exc

    agents_md_path = root / "AGENTS.md"
    agents_md_created = False
    if not agents_md_path.exists():
        try:
            agents_template_file = resources.files(_AGENTS_TEMPLATE_PACKAGE) / "templates" / "agents-template.md"
            if agents_template_file.is_file():
                content = agents_template_file.read_text(encoding="utf-8").replace("[PROJECT_NAME]", root.name)
                agents_md_path.write_text(content, encoding="utf-8")
                agents_md_created = True
        except (OSError, UnicodeError, AttributeError, ModuleNotFoundError, TypeError):
            pass

    stale = sum(1 for e in plan_entries if e.needs_generation)
    console.print(f"[bold green]done[/bold green] initialized {root}")
    console.print(
        f"  graph: {len(result.build_ctx.graph.nodes)} nodes, "
        f"{len(result.build_ctx.graph.edges)} edges, {result.community_count} communities"
    )
    console.print(f"  docs plan: {len(plan_entries)} entries, {stale} need (re)generation")
    console.print(f"  .agents/: {len(sync_report.created)} file(s) added, "
                  f"{len(sync_report.kept_existing)} already present (left untouched)")
    if agents_md_created:
        console.print(f"  wrote: {agents_md_path}")
    console.print(f"  wrote: {json_path}")
    console.print(f"  wrote: {db_path}")
    console.print(f"  wrote: {html_path}")
    console.print(f"  wrote: {plan_path}")
    console.print(
        "  next: open this codebase in Antigravity and run /document-codebase, then start a feature with /specify"
    )
