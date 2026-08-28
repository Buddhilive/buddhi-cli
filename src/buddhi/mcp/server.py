from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("buddhi-cli")

# Global DB path override if provided via CLI argument
OVERRIDE_DB_PATH: Path | None = None


def _get_db_path(cwd: str | None = None) -> Path:
    """Resolve the SQLite graph database path.

    1. Use the command-line override if set.
    2. Traverse upwards from CWD (or given cwd) to auto-detect .buddhi/graphs/tree-graph.db.
    3. Fallback to (cwd)/.buddhi/graphs/tree-graph.db if not found.
    """
    if OVERRIDE_DB_PATH is not None:
        return OVERRIDE_DB_PATH

    start_dir = Path(cwd).resolve() if cwd else Path.cwd().resolve()
    for parent in [start_dir] + list(start_dir.parents):
        for rel in [
            Path(".buddhi") / "graphs" / "tree-graph.db",
            Path(".buddhi") / "tree-graph.db",
            Path(".buddhi") / "graph.db",
        ]:
            candidate = parent / rel
            if candidate.exists():
                return candidate

    # Standard fallback
    return start_dir / ".buddhi" / "graphs" / "tree-graph.db"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_search(
    query: Annotated[
        str,
        "Search query — function names, class names, or natural-language descriptions of code behavior",
    ],
    top_n: Annotated[int, "Number of top lexical anchors to retrieve"] = 3,
    mode: Annotated[
        str,
        "Output mode: 'full' (complete source), 'signatures' (declarations only), or 'map' (one-liner index)",
    ] = "full",
    include_bridges: Annotated[bool, "Include 1-hop bridge nodes from neighboring communities"] = True,
    budget: Annotated[int, "Max character count for output. 0 = unbounded"] = 8000,
    cwd: Annotated[str | None, "Working directory override. Defaults to CWD of the MCP server process."] = None,
) -> str:
    """Search the codebase using Buddhi's topology-driven retrieval pipeline.

    This replaces standard keyword-only searches with community-aware,
    context-optimized results. It identifies lexical anchors, expands to community
    neighborhoods, filters out boilerplate, and sorts using a U-curve positional layout.
    """
    from buddhi.mcp.tools.search import execute_buddhi_search

    db_path = _get_db_path(cwd)
    try:
        return execute_buddhi_search(
            query=query,
            db_path=str(db_path),
            top_n=top_n,
            mode=mode,
            include_bridges=include_bridges,
            budget=budget,
        )
    except Exception as e:
        return f"Error executing search: {e}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_read(
    filepath: Annotated[str | None, "The workspace path to the file to read"] = None,
    query: Annotated[str | None, "Glob pattern or identifier to find files/symbols in the workspace"] = None,
    mode: Annotated[str, "Compression profile: 'auto', 'full', 'signatures', 'map', or 'entropy'"] = "auto",
    task_intent: Annotated[str | None, "Natural language goals (e.g. 'Fix the bug') to auto-resolve mode"] = None,
    budget: Annotated[int, "Max token count budget. Fallbacks to map if exceeded"] = 4000,
    cwd: Annotated[str | None, "Working directory override. Defaults to CWD of the MCP server process."] = None,
) -> str:
    """Read a file using dynamic compression, AST pruning, and bounce prevention logic, or search for files/symbols in the workspace."""
    from buddhi.mcp.tools.read import execute_buddhi_read

    db_path = _get_db_path(cwd)
    try:
        return execute_buddhi_read(
            filepath=filepath,
            db_path=str(db_path) if db_path.exists() else None,
            mode=mode,
            task_intent=task_intent,
            budget=budget,
            query=query,
        )
    except Exception as e:
        return f"Error executing read: {e}"


def main() -> None:
    """CLI entrypoint for running the MCP server."""
    parser = argparse.ArgumentParser(description="Buddhi MCP Server (StdIO)")
    parser.add_argument(
        "--db-path",
        type=str,
        help="Explicit path to the .buddhi/graphs/tree-graph.db database (overrides auto-detection)",
    )

    args, unknown = parser.parse_known_args()

    if args.db_path:
        global OVERRIDE_DB_PATH
        OVERRIDE_DB_PATH = Path(args.db_path).resolve()

    sys.argv = [sys.argv[0]] + unknown
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
