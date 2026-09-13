from __future__ import annotations

from pathlib import Path

import typer


def mcp_cmd(
    db_path: Path | None = typer.Option(  # noqa: B008
        None,
        "--db-path",
        help="Explicit path to the .buddhi/graphs/tree-graph.db database (overrides auto-detection)",
    ),
    root: Path | None = typer.Option(  # noqa: B008
        None,
        "--root",
        "-r",
        help="Explicit path to the workspace root directory",
    ),
) -> None:
    """Run the Buddhi Model Context Protocol (MCP) server over StdIO."""
    try:
        from buddhi.mcp.server import mcp
    except ImportError as e:
        typer.secho(
            f"Error: MCP dependencies are not installed. Install with `pip install buddhi-ai[mcp]`: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from e

    if db_path or root:
        import buddhi.mcp.server as server_mod

        if db_path:
            server_mod.OVERRIDE_DB_PATH = db_path.resolve()
        if root:
            server_mod.OVERRIDE_ROOT = root.resolve()

    mcp.run(transport="stdio")
