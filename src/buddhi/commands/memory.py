"""Typer CLI command group for OKF v0.2 + Claude Code memory bundle operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from buddhi.memory.hash import compute_content_hash
from buddhi.memory.migrate import migrate_legacy_memory
from buddhi.memory.models import (
    MemoryConfidence,
    MemoryFrontmatter,
    MemoryKind,
    MemoryNode,
    MemorySource,
    MemoryStatus,
)
from buddhi.memory.security import sanitize_slug
from buddhi.memory.store import MemoryStore

console = Console()
err_console = Console(stderr=True)

memory_app = typer.Typer(
    help="Google OKF v0.2 & Claude Code memory bundle management.",
    no_args_is_help=True,
)


@memory_app.command(
    name="status", help="Check MEMORY.md entrypoint budget and staleness telemetry."
)
def status_cmd(
    scope: Annotated[
        str, typer.Option("--scope", help="Memory scope to inspect.")
    ] = "project",
    as_json: Annotated[
        bool, typer.Option("--json", help="Output results as JSON.")
    ] = False,
) -> None:
    store = MemoryStore(Path.cwd())
    val = store.validate_bundle(scope=scope)

    if as_json:
        console.print(json.dumps(val, indent=2))
        return

    table = Table(title=f"Memory Bundle Status ({scope})", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Concepts", str(val["total_nodes"]))
    table.add_row("MEMORY.md Lines", f"{val['budget']['total_lines']} / 200")
    table.add_row("MEMORY.md Bytes", f"{val['budget']['total_bytes']} / 25600 bytes")
    table.add_row(
        "Budget Valid",
        "[green]PASS[/green]" if val["budget"]["is_valid"] else "[red]FAIL[/red]",
    )
    table.add_row("Stale Concepts", str(len(val["stale_nodes"])))
    table.add_row("Broken Relations", str(len(val["broken_relations"])))

    console.print(table)

    if val["stale_nodes"]:
        console.print("\n[yellow]Stale Concepts (source hash mismatch):[/yellow]")
        for stale in val["stale_nodes"]:
            console.print(
                f"  - [bold]{stale['node_id']}[/bold]: {stale['resource']} ({stale['reason']})"
            )

    if val["budget"]["violations"]:
        console.print("\n[red]Budget Violations:[/red]")
        for v in val["budget"]["violations"]:
            console.print(f"  - {v}")


@memory_app.command(name="add", help="Add or update an atomic OKF memory concept node.")
def add_cmd(
    kind: Annotated[
        str,
        typer.Option(
            "--kind",
            "-k",
            help="Concept kind (decision, convention, preference, feedback, sdd-rationale).",
        ),
    ],
    title: Annotated[str, typer.Option("--title", "-t", help="Concept title.")],
    summary: Annotated[
        str, typer.Option("--summary", "-s", help="One-sentence concept summary.")
    ],
    body: Annotated[str, typer.Option("--body", "-b", help="Markdown body text.")] = "",
    path_glob: Annotated[
        list[str] | None,
        typer.Option("--path-glob", "-p", help="Path glob pattern for activation."),
    ] = None,
    source: Annotated[
        list[str] | None,
        typer.Option("--source", help="Source code anchor (file.py#L1-L20)."),
    ] = None,
    scope: Annotated[
        str, typer.Option("--scope", help="Target scope (project, local, user).")
    ] = "project",
    tag: Annotated[
        list[str] | None, typer.Option("--tag", help="Concept tags.")
    ] = None,
) -> None:
    ws_root = Path.cwd()
    store = MemoryStore(ws_root)

    try:
        kind_enum = MemoryKind(kind)
    except ValueError:
        err_console.print(f"[red]error:[/red] invalid kind: {kind}")
        raise typer.Exit(code=1)

    slug = sanitize_slug(title)
    node_id = f"mem-{kind_enum.value}-{slug}"

    sources: list[MemorySource] = []
    if source:
        for idx, src_ref in enumerate(source, 1):
            try:
                chash = compute_content_hash(ws_root, src_ref)
                sources.append(
                    MemorySource(id=f"src-{idx}", resource=src_ref, content_hash=chash)
                )
            except (OSError, ValueError) as exc:
                err_console.print(
                    f"[yellow]warning:[/yellow] could not hash source '{src_ref}': {exc}"
                )

    node = MemoryNode(
        frontmatter=MemoryFrontmatter(
            id=node_id,
            kind=kind_enum,
            title=title,
            summary=summary,
            status=MemoryStatus.STABLE,
            confidence=MemoryConfidence.VERIFIED,
            scope=scope,
            paths=path_glob or [],
            tags=tag or [],
            sources=sources,
        ),
        body=f"# Summary\n\n{summary}\n\n# Context & Rationale\n\n{body}\n"
        if body
        else f"# Summary\n\n{summary}\n",
    )

    try:
        saved_path = store.save_node(node, scope=scope)
        console.print(
            f"[green]Saved memory concept:[/green] [bold]{node_id}[/bold] -> {saved_path}"
        )
    except (OSError, ValueError, PermissionError) as exc:
        err_console.print(f"[red]error saving memory concept:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@memory_app.command(
    name="search",
    help="Search memory concepts across scopes with query and path glob filtering.",
)
def search_cmd(
    query: Annotated[str | None, typer.Argument(help="Search query.")] = None,
    kind: Annotated[
        str | None, typer.Option("--kind", "-k", help="Filter by kind.")
    ] = None,
    scope: Annotated[
        str, typer.Option("--scope", help="Memory scope to search.")
    ] = "project",
    active_file: Annotated[
        list[str] | None,
        typer.Option(
            "--active-file", "-f", help="Active files for path glob filtering."
        ),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Output results as JSON.")
    ] = False,
) -> None:
    from buddhi.mcp.tools.memory import execute_buddhi_memory

    raw_json = execute_buddhi_memory(
        action="search",
        query=query,
        kind=kind,
        scope=scope,
        active_files=active_file,
    )
    if as_json:
        console.print(raw_json)
        return

    data = json.loads(raw_json)
    memories = data.get("memories", [])
    if not memories:
        console.print("[yellow]No matching memory concepts found.[/yellow]")
        return

    table = Table(title=f"Memory Search Results ({len(memories)})", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Kind", style="green")
    table.add_column("Title", style="bold")
    table.add_column("Summary", style="white")

    for m in memories:
        table.add_row(m["id"], m["kind"], m["title"], m["summary"][:80])
    console.print(table)


@memory_app.command(
    name="read", help="Read a memory concept node with optional @path import expansion."
)
def read_cmd(
    node_id: Annotated[str, typer.Argument(help="Exact memory concept ID to read.")],
    scope: Annotated[
        str, typer.Option("--scope", help="Memory scope to read from.")
    ] = "project",
    expand_imports: Annotated[
        bool,
        typer.Option(
            "--expand-imports/--no-expand-imports", help="Expand @path imports inline."
        ),
    ] = True,
) -> None:
    from buddhi.mcp.tools.memory import execute_buddhi_memory

    out = execute_buddhi_memory(
        action="read",
        node_id=node_id,
        scope=scope,
        expand_imports=expand_imports,
    )
    console.print(out)


@memory_app.command(
    name="validate",
    help="Validate OKF bundle frontmatter, budget limits, and staleness.",
)
def validate_cmd(
    scope: Annotated[
        str, typer.Option("--scope", help="Memory scope to validate.")
    ] = "project",
    as_json: Annotated[
        bool, typer.Option("--json", help="Output results as JSON.")
    ] = False,
) -> None:
    store = MemoryStore(Path.cwd())
    val = store.validate_bundle(scope=scope)

    if as_json:
        console.print(json.dumps(val, indent=2))
    else:
        if val["is_valid"]:
            console.print(
                f"[green]PASS:[/green] Memory bundle ({scope}) is compliant and current."
            )
        else:
            console.print(f"[red]FAIL:[/red] Memory bundle ({scope}) has violations:")
            for v in val["budget"]["violations"]:
                console.print(f"  - [red]Budget:[/red] {v}")
            for s in val["stale_nodes"]:
                console.print(
                    f"  - [yellow]Stale source:[/yellow] {s['node_id']} ({s['resource']})"
                )

    if not val["is_valid"]:
        raise typer.Exit(code=1)


@memory_app.command(
    name="sync", help="Reconcile topic index.md files and MEMORY.md entrypoint."
)
def sync_cmd(
    scope: Annotated[
        str, typer.Option("--scope", help="Memory scope to sync.")
    ] = "project",
) -> None:
    store = MemoryStore(Path.cwd())
    store.sync_indexes(scope=scope)
    console.print(
        f"[green]Synced index files and MEMORY.md for scope '{scope}'.[/green]"
    )


@memory_app.command(
    name="compact",
    help="Demote lower-priority pointers from MEMORY.md to maintain 200-line budget.",
)
def compact_cmd(
    scope: Annotated[
        str, typer.Option("--scope", help="Memory scope to compact.")
    ] = "project",
) -> None:
    store = MemoryStore(Path.cwd())
    violations = store.compact(scope=scope)
    if violations:
        console.print("[yellow]Compacted, but remaining budget violations:[/yellow]")
        for v in violations:
            console.print(f"  - {v}")
    else:
        console.print(
            f"[green]Compaction successful. MEMORY.md within budget for '{scope}'.[/green]"
        )


@memory_app.command(
    name="migrate", help="Migrate legacy flat-file memory into OKF concept bundles."
)
def migrate_cmd() -> None:
    res = migrate_legacy_memory(Path.cwd())
    console.print(
        f"[green]Migrated {res.migrated_count} legacy entries to OKF concepts.[/green]"
    )
    for created in res.created_nodes:
        console.print(f"  + {created}")


@memory_app.command(
    name="sdd-promote",
    help="Promote durable decisions and choices from an SDD feature spec into OKF memory.",
)
def sdd_promote_cmd(
    branch: Annotated[
        str | None,
        typer.Option("--branch", help="Specific feature branch under .buddhi/specs/."),
    ] = None,
) -> None:
    from buddhi.memory.sdd_promote import promote_sdd_artifacts

    result = promote_sdd_artifacts(Path.cwd(), branch=branch)
    if not result.promoted_nodes:
        console.print(
            f"[yellow]No promotable SDD decisions or sound choices found for branch '{branch or 'active'}'.[/yellow]"
        )
        return

    console.print(
        f"[green]Promoted {len(result.promoted_nodes)} SDD concept(s) from branch '{result.spec_branch}':[/green]"
    )
    for node in result.promoted_nodes:
        console.print(f"  + [bold]{node.id}[/bold] ({node.kind.value}): {node.title}")
