import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from buddhi_ai.metrics.logger import MetricsLogger

# We initialize FastMCP with the approved server name
mcp = FastMCP("buddhi-cli")

# Store the global DB path override if provided via CLI
OVERRIDE_DB_PATH: Path | None = None

def _get_db_path(cwd: Optional[str] = None) -> Path:
    """Resolve the sqlite DB path.
    
    1. Use the command-line override if set.
    2. Traverse upwards from CWD to auto-detect .buddhi/graph.db.
    3. Fallback to CWD/.buddhi/graph.db if not found.
    """
    if OVERRIDE_DB_PATH is not None:
        return OVERRIDE_DB_PATH

    env_path = os.environ.get("BUDDHI_DB_PATH")
    if env_path:
        return Path(env_path).resolve()
    
    # Auto-detect from CWD and walk up directories
    current = Path(cwd).resolve() if cwd else Path.cwd().resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / ".buddhi" / "graph.db"
        if candidate.exists():
            return candidate
            
    # Standard CWD fallback if not found anywhere in parent tree
    return current / ".buddhi" / "graph.db"

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_search(
    query: Annotated[str, "Search query — function names, class names, or natural-language descriptions of code behavior"],
    top_n: Annotated[int, "Number of top lexical anchors to retrieve"] = 3,
    mode: Annotated[str, "Output mode: 'full' (complete source), 'signatures' (declarations only), or 'map' (one-liner index)"] = "full",
    include_bridges: Annotated[bool, "Include 1-hop bridge nodes from neighboring communities"] = True,
    budget: Annotated[int, "Max character count for output. 0 = unbounded"] = 8000,
    cwd: Annotated[Optional[str], "Working directory override. Defaults to CWD of the MCP server process."] = None,
) -> str:
    """Search the codebase using Buddhi's topology-driven retrieval pipeline.
    
    This replaces standard keyword-only searches with community-aware, 
    context-optimized results. It identifies lexical anchors, expands to community
    neighborhoods, filters out boilerplate, and sorts using a U-curve positional layout.
    """
    from buddhi_ai.search.search import buddhi_search as _search

    db_path = _get_db_path(cwd)
    if not db_path.exists():
        return f"Error: Buddhi database not found at '{db_path}'. Please run `buddhi init` in this directory first."

    start_time = time.perf_counter()
    status = "success"
    error_message = None
    result = ""

    try:
        result = _search(
            query=query,
            db_path=str(db_path),
            top_n=top_n,
            mode=mode,
            include_bridges=include_bridges,
            budget=budget,
        )
        return result
    except Exception as e:
        status = "error"
        error_message = str(e)
        result = f"Error executing search: {str(e)}"
        return result
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        input_tokens = MetricsLogger.count_tokens(json.dumps({
            "query": query, "top_n": top_n, "mode": mode,
            "include_bridges": include_bridges, "budget": budget
        }))
        output_tokens = MetricsLogger.count_tokens(result) if status == "success" else 0
        
        MetricsLogger.log(
            tool_name="buddhi_search",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_input_tokens=0,
            tokens_saved=0,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_read(
    filepath: Annotated[str, "The workspace path to the file to read"],
    mode: Annotated[str, "Compression profile: 'auto', 'full', 'signatures', 'map', or 'entropy'"] = "auto",
    task_intent: Annotated[Optional[str], "Natural language goals (e.g. 'Fix the bug') to auto-resolve mode"] = None,
    budget: Annotated[int, "Max token count budget. Fallbacks to map if exceeded"] = 4000,
    cwd: Annotated[Optional[str], "Working directory override. Defaults to CWD of the MCP server process."] = None,
) -> str:
    """Read a file using dynamic compression, AST pruning, and bounce prevention logic to prevent prompt thrashing."""
    from buddhi_ai.mcp.tools.read import execute_buddhi_read

    db_path = _get_db_path(cwd)

    start_time = time.perf_counter()
    status = "success"
    error_message = None
    result = ""
    raw_input_tokens = 0

    try:
        # Calculate raw file tokens for savings
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_input_tokens = MetricsLogger.count_tokens(f.read())
        except Exception:
            pass # ignore read errors here, execute_buddhi_read will handle it

        result = execute_buddhi_read(
            filepath=filepath,
            db_path=str(db_path) if db_path.exists() else None,
            mode=mode,
            task_intent=task_intent,
            budget=budget,
        )
        if result.startswith("Error:"):
            status = "error"
            error_message = result
        return result
    except Exception as e:
        status = "error"
        error_message = str(e)
        result = f"Error executing read: {str(e)}"
        return result
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        input_tokens = MetricsLogger.count_tokens(json.dumps({
            "filepath": filepath, "mode": mode,
            "task_intent": task_intent, "budget": budget
        }))
        output_tokens = MetricsLogger.count_tokens(result) if status == "success" else 0
        tokens_saved = max(0, raw_input_tokens - output_tokens) if status == "success" else 0
        
        MetricsLogger.log(
            tool_name="buddhi_read",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_input_tokens=raw_input_tokens,
            tokens_saved=tokens_saved,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )


@mcp.tool()
def buddhi_shell(
    command: Annotated[str, "The shell command to execute. Must be non-interactive."],
    timeout: Annotated[int, "Max seconds to wait before killing the process"] = 60,
    budget: Annotated[int, "Max token count for the compressed output. 0 = unbounded"] = 8000,
    raw: Annotated[bool, "Skip compression pipeline and return raw output (up to budget)"] = False,
    cwd: Annotated[Optional[str], "Working directory override. Defaults to CWD of the MCP server process."] = None,
) -> str:
    """Execute a shell command and return compressed, token-efficient output.

    The output passes through a 4-phase pipeline:
      1. Noise eradication (ANSI, progress bars, garbled UTF-8)
      2. Domain-specific abstraction (Git, Linter/Compiler, Stack Traces)
      3. Structural deduplication (Rabin-Karp rolling hash)
      4. Compact Response Protocol (delta symbols, path aliases, token budget)

    Set ``raw=True`` to bypass compression and receive unmodified output
    (still hard-capped at *budget* tokens).
    """
    from buddhi_ai.mcp.tools.shell import run_command
    from buddhi_ai.mcp.compression.pipeline import process

    start_time = time.perf_counter()
    status = "success"
    error_message = None
    result = ""
    raw_input_tokens = 0

    try:
        try:
            raw_output, exit_code = run_command(command, timeout=timeout, cwd=cwd)
            raw_input_tokens = MetricsLogger.count_tokens(raw_output)
        except RuntimeError as exc:
            # Interactive command was blocked
            status = "error"
            error_message = str(exc)
            result = str(exc)
            return result

        # Prepend exit-code header so the LLM always knows the result
        header = f"[exit:{exit_code}] $ {command}\n"
        compressed = process(raw_output, budget=budget, raw_mode=raw)
        result = header + compressed
        return result
    except Exception as e:
        status = "error"
        error_message = str(e)
        result = str(e)
        return result
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        input_tokens = MetricsLogger.count_tokens(json.dumps({
            "command": command, "timeout": timeout,
            "budget": budget, "raw": raw, "cwd": cwd
        }))
        output_tokens = MetricsLogger.count_tokens(result) if status == "success" else 0
        tokens_saved = max(0, raw_input_tokens - output_tokens) if status == "success" else 0
        
        MetricsLogger.log(
            tool_name="buddhi_shell",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_input_tokens=raw_input_tokens,
            tokens_saved=tokens_saved,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )


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
