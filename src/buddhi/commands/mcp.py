from __future__ import annotations

from pathlib import Path
import typer


def mcp_cmd(
    db_path: Path | None = typer.Option(
        None,
        "--db-path",
        help="Explicit path to the .buddhi/graphs/tree-graph.db database (overrides auto-detection)",
    ),
) -> None:
    """Run the Buddhi Model Context Protocol (MCP) server over StdIO."""
    try:
        from buddhi.mcp.server import OVERRIDE_DB_PATH, mcp
    except ImportError as e:
        typer.secho(
            f"Error: MCP dependencies are not installed. Install with `pip install buddhi-ai[mcp]`: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from e

    if db_path:
        import buddhi.mcp.server as server_mod

        server_mod.OVERRIDE_DB_PATH = db_path.resolve()

    mcp.run(transport="stdio")
