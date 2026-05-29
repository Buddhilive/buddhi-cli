import argparse
import sys
from pathlib import Path
from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

# We initialize FastMCP with the approved server name
mcp = FastMCP("buddhi-cli")

# Store the global DB path override if provided via CLI
OVERRIDE_DB_PATH: Path | None = None

def _get_db_path() -> Path:
    """Resolve the sqlite DB path.
    
    1. Use the command-line override if set.
    2. Traverse upwards from CWD to auto-detect .buddhi/graph.db.
    3. Fallback to CWD/.buddhi/graph.db if not found.
    """
    if OVERRIDE_DB_PATH is not None:
        return OVERRIDE_DB_PATH
    
    # Auto-detect from CWD and walk up directories
    current = Path.cwd().resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / ".buddhi" / "graph.db"
        if candidate.exists():
            return candidate
            
    # Standard CWD fallback if not found anywhere in parent tree
    return Path.cwd().resolve() / ".buddhi" / "graph.db"

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_search(
    query: Annotated[str, "Search query — function names, class names, or natural-language descriptions of code behavior"],
    top_n: Annotated[int, "Number of top lexical anchors to retrieve"] = 3,
    mode: Annotated[str, "Output mode: 'full' (complete source), 'signatures' (declarations only), or 'map' (one-liner index)"] = "full",
    include_bridges: Annotated[bool, "Include 1-hop bridge nodes from neighboring communities"] = True,
    budget: Annotated[int, "Max character count for output. 0 = unbounded"] = 8000,
) -> str:
    """Search the codebase using Buddhi's topology-driven retrieval pipeline.
    
    This replaces standard keyword-only searches with community-aware, 
    context-optimized results. It identifies lexical anchors, expands to community
    neighborhoods, filters out boilerplate, and sorts using a U-curve positional layout.
    """
    from buddhi_ai.search.search import buddhi_search as _search
    
    db_path = _get_db_path()
    if not db_path.exists():
        return f"Error: Buddhi database not found at '{db_path}'. Please run `buddhi init` in this directory first."
        
    try:
        return _search(
            query=query,
            db_path=str(db_path),
            top_n=top_n,
            mode=mode,
            include_bridges=include_bridges,
            budget=budget,
        )
    except Exception as e:
        return f"Error executing search: {str(e)}"

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_read(
    filepath: Annotated[str, "The workspace path to the file to read"],
    mode: Annotated[str, "Compression profile: 'auto', 'full', 'signatures', 'map', or 'entropy'"] = "auto",
    task_intent: Annotated[Optional[str], "Natural language goals (e.g. 'Fix the bug') to auto-resolve mode"] = None,
    budget: Annotated[int, "Max token count budget. Fallbacks to map if exceeded"] = 4000,
) -> str:
    """Read a file using dynamic compression, AST pruning, and bounce prevention logic to prevent prompt thrashing."""
    from buddhi_ai.mcp.tools.read import execute_buddhi_read
    
    db_path = _get_db_path()
    if not db_path.exists():
        return f"Error: Buddhi database not found at '{db_path}'. Please run `buddhi init` in this directory first."
        
    try:
        return execute_buddhi_read(
            filepath=filepath,
            db_path=str(db_path),
            mode=mode,
            task_intent=task_intent,
            budget=budget,
        )
    except Exception as e:
        return f"Error executing read: {str(e)}"


def main() -> None:
    """CLI entrypoint for running the MCP server."""
    parser = argparse.ArgumentParser(description="Buddhi MCP Server (StdIO)")
    parser.add_argument(
        "--db-path",
        type=str,
        help="Explicit path to the .buddhi/graph.db database (overrides auto-detection)",
    )
    
    # Parse only known args to let FastMCP capture any remaining arguments
    args, unknown = parser.parse_known_args()
    
    if args.db_path:
        global OVERRIDE_DB_PATH
        OVERRIDE_DB_PATH = Path(args.db_path).resolve()
        
    # Run the FastMCP server over stdio
    # Pass along any unknown arguments to mcp.run (FastMCP CLI support)
    sys.argv = [sys.argv[0]] + unknown
    mcp.run(transport="stdio")
