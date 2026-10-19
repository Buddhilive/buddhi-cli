"""Typer CLI command group for code graph analysis and blast radius."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from buddhi.mcp.tools.graph import execute_buddhi_graph

graph_app = typer.Typer(
    help="Code graph topology, blast radius, and architectural analysis.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _resolve_db_path(root: Path) -> Path:
    return root / ".buddhi" / "graphs" / "tree-graph.db"


@graph_app.command(
    name="blast-radius",
    help="Analyze blast radius impact for files, symbols, or git diff.",
)
def blast_radius_cmd(
    targets: Annotated[
        list[str] | None, typer.Argument(help="Target files or symbols")
    ] = None,
    git_ref: str | None = typer.Option(
        None, "--git-ref", help="Git revision or range to diff"
    ),
    staged: bool = typer.Option(
        False, "--staged", help="Diff staged index against HEAD"
    ),
    max_hops: int = typer.Option(
        3, "--max-hops", help="Max reverse caller traversal hops (1-6)"
    ),
    as_json: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    root = Path.cwd().resolve()
    db_path = _resolve_db_path(root)
    output = execute_buddhi_graph(
        action="blast_radius",
        db_path=str(db_path),
        root_path=root,
        targets=targets,
        git_ref=git_ref,
        staged=staged,
        max_hops=max_hops,
        as_json=as_json,
    )
    if as_json:
        print(output)
    else:
        console.print(output)


@graph_app.command(
    name="analyze",
    help="Display top god nodes, surprising links, and review questions.",
)
def analyze_cmd(
    top_n: int = typer.Option(10, "--top", help="Top items to display"),
    as_json: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    root = Path.cwd().resolve()
    db_path = _resolve_db_path(root)
    if as_json:
        gods = json.loads(
            execute_buddhi_graph(
                "god_nodes", str(db_path), root_path=root, top_n=top_n, as_json=True
            )
        )
        surprises = json.loads(
            execute_buddhi_graph(
                "surprises", str(db_path), root_path=root, top_n=top_n, as_json=True
            )
        )
        questions = json.loads(
            execute_buddhi_graph(
                "questions", str(db_path), root_path=root, top_n=top_n, as_json=True
            )
        )
        print(
            json.dumps(
                {
                    "god_nodes": gods,
                    "surprising_connections": surprises,
                    "suggested_questions": questions,
                },
                indent=2,
            )
        )
    else:
        console.print(
            execute_buddhi_graph("god_nodes", str(db_path), root_path=root, top_n=top_n)
        )
        console.print("")
        console.print(
            execute_buddhi_graph("surprises", str(db_path), root_path=root, top_n=top_n)
        )
        console.print("")
        console.print(
            execute_buddhi_graph("questions", str(db_path), root_path=root, top_n=top_n)
        )


@graph_app.command(name="path", help="Find shortest path between two symbols.")
def path_cmd(
    source: str = typer.Argument(..., help="Source symbol name or ID"),
    target: str = typer.Argument(..., help="Target symbol name or ID"),
    max_hops: int = typer.Option(8, "--max-hops", help="Maximum hops to search"),
    as_json: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    root = Path.cwd().resolve()
    db_path = _resolve_db_path(root)
    output = execute_buddhi_graph(
        "shortest_path",
        str(db_path),
        root_path=root,
        source=source,
        target=target,
        max_hops=max_hops,
        as_json=as_json,
    )
    if as_json:
        print(output)
    else:
        console.print(output)


@graph_app.command(name="cycles", help="Find circular imports in the codebase.")
def cycles_cmd(
    max_cycles: int = typer.Option(20, "--max-cycles", help="Maximum cycles to find"),
    as_json: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    root = Path.cwd().resolve()
    db_path = _resolve_db_path(root)
    output = execute_buddhi_graph(
        "cycles", str(db_path), root_path=root, top_n=max_cycles, as_json=as_json
    )
    if as_json:
        print(output)
    else:
        console.print(output)


@graph_app.command(name="community", help="Inspect communities and cohesion.")
def community_cmd(
    community_id: int | None = typer.Argument(
        None, help="Specific community ID to inspect"
    ),
    as_json: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    root = Path.cwd().resolve()
    db_path = _resolve_db_path(root)
    output = execute_buddhi_graph(
        "community",
        str(db_path),
        root_path=root,
        community_id=community_id,
        as_json=as_json,
    )
    if as_json:
        print(output)
    else:
        console.print(output)


@graph_app.command(
    name="stats", help="Show code graph counts, confidence breakdown, and staleness."
)
def stats_cmd(
    as_json: bool = typer.Option(False, "--json", help="Output JSON format"),
) -> None:
    root = Path.cwd().resolve()
    db_path = _resolve_db_path(root)
    output = execute_buddhi_graph(
        "stats", str(db_path), root_path=root, as_json=as_json
    )
    if as_json:
        print(output)
    else:
        console.print(output)
