from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import typer
from rich.console import Console

from buddhi.docgen.planner import build_docs_plan, plan_to_json
from buddhi.graph.pipeline import run_pipeline
from buddhi.memory.migrate import migrate_legacy_memory
from buddhi.persist.html_writer import write_html
from buddhi.persist.json_writer import write_json
from buddhi.persist.sqlite_writer import write_sqlite
from buddhi.util.fsutil import (
    BuddhiFsError,
    ensure_agents_gitignore,
    ensure_buddhi_dirs,
    ensure_docs_dir,
    migrate_legacy_plan_skill,
    migrate_legacy_tasks_skill,
    migrate_legacy_workflows,
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
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Print per-file warnings."
    ),
) -> None:
    """Build the code graph, plan docs, and scaffold a Google Antigravity agent harness.

    The harness covers doc generation plus a general full-stack planning layer
    (frontend/backend/database/testing/security/deployment/git specialist
    agents, orchestrated by the /spec-plan skill). Idempotent: rerunning never
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
            err_console.print(
                f"[yellow]warning:[/yellow] language '{lang}' unavailable: {err}"
            )
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
        write_sqlite(
            result.build_ctx.graph,
            db_path,
            root_path=str(root),
            extract_cache_entries=result.build_ctx.extract_cache_entries,
        )
        write_html(result.build_ctx.graph, html_path, root_label=root.name or str(root))
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing graph artifacts: {exc}")
        raise typer.Exit(code=1) from exc

    plan_entries = build_docs_plan(result.build_ctx.graph, root)
    plan_path = root / ".buddhi" / "docs-plan.json"
    try:
        plan_path.write_text(
            json.dumps(plan_to_json(plan_entries), indent=2), encoding="utf-8"
        )
    except OSError as exc:
        err_console.print(f"[red]error:[/red] failed writing {plan_path}: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        plan_migration_report = migrate_legacy_plan_skill(
            root / ".agents", project_root=root
        )
        tasks_migration_report = migrate_legacy_tasks_skill(
            root / ".agents", project_root=root
        )
        memory_migration_report = migrate_legacy_memory(root)
        ensure_agents_gitignore(root / ".agents")
        template_root = resources.files(_AGENTS_TEMPLATE_PACKAGE)
        with resources.as_file(template_root) as template_dir:
            sync_report = sync_template_tree(template_dir, root / ".agents")
        migration_report = migrate_legacy_workflows(root / ".agents")
    except (BuddhiFsError, ModuleNotFoundError, FileNotFoundError) as exc:
        err_console.print(f"[red]error:[/red] failed scaffolding .agents/: {exc}")
        raise typer.Exit(code=1) from exc

    mcp_config_path = root / ".agents" / "mcp_config.json"
    if mcp_config_path.exists():
        try:
            mcp_data = json.loads(mcp_config_path.read_text(encoding="utf-8"))
            if "mcpServers" in mcp_data and "buddhi" in mcp_data["mcpServers"]:
                buddhi_server = mcp_data["mcpServers"]["buddhi"]
                current_args = list(buddhi_server.get("args", []))
                if "--root" in current_args:
                    idx = current_args.index("--root")
                    if idx + 1 < len(current_args):
                        current_args[idx + 1] = str(root.resolve())
                    else:
                        current_args.append(str(root.resolve()))
                    buddhi_server["args"] = current_args
                else:
                    buddhi_server["args"] = ["--root", str(root.resolve())]
                mcp_config_path.write_text(
                    json.dumps(mcp_data, indent=2) + "\n", encoding="utf-8"
                )
        except (json.JSONDecodeError, OSError) as exc:
            if verbose:
                err_console.print(
                    f"[yellow]warning:[/yellow] could not configure .agents/mcp_config.json: {exc}"
                )

    agents_md_path = root / "AGENTS.md"
    agents_md_created = False
    if not agents_md_path.exists():
        try:
            agents_template_file = (
                resources.files(_AGENTS_TEMPLATE_PACKAGE)
                / "templates"
                / "agents-template.md"
            )
            if agents_template_file.is_file():
                content = agents_template_file.read_text(encoding="utf-8").replace(
                    "[PROJECT_NAME]", root.name
                )
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
    console.print(
        f"  docs plan: {len(plan_entries)} entries, {stale} need (re)generation"
    )
    console.print(
        f"  .agents/: {len(sync_report.created)} file(s) added, "
        f"{len(sync_report.kept_existing)} already present (left untouched)"
    )
    if (
        plan_migration_report.migrated_skill
        or plan_migration_report.removed_legacy_skill
    ):
        console.print("  migrated legacy plan skill to spec-plan")
    if (
        tasks_migration_report.migrated_skill
        or tasks_migration_report.removed_legacy_skill
    ):
        console.print("  migrated legacy tasks skill to spec-tasks")
    if memory_migration_report.migrated_count > 0:
        console.print(
            f"  migrated legacy memory: {memory_migration_report.migrated_count} entry(ies) converted to OKF concepts"
        )
    if migration_report.migrated or migration_report.removed:
        console.print(
            f"  migrated legacy workflows: {len(migration_report.migrated)} converted to skills, "
            f"{len(migration_report.removed)} legacy workflow file(s) removed"
        )
    if agents_md_created:
        console.print(f"  wrote: {agents_md_path}")
    console.print(f"  wrote: {json_path}")
    console.print(f"  wrote: {db_path}")
    console.print(f"  wrote: {html_path}")
    console.print(f"  wrote: {plan_path}")
    console.print(
        "  next: open this codebase in Antigravity and run /document-codebase, then start a feature with /specify"
    )
