import sqlite3
import logging
import json
from pathlib import Path
from typing import Optional, List

from buddhi_ai.mcp.compression.telemetry import log_read_event, should_trip_circuit_breaker
from buddhi_ai.mcp.compression.classifier import resolve_mode
from buddhi_ai.mcp.compression.entropy import filter_by_entropy, count_tokens
from buddhi_ai.mcp.compression.ast_pruner import prune_signatures, extract_map


def _write_fallback_allowed(tool_name: str) -> None:
    """Flag that a fallback to native tools is allowed in gate_io."""
    try:
        fallback_path = Path(".buddhi/fallback_allowed.json")
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        allowed = {}
        if fallback_path.exists():
            with open(fallback_path, "r", encoding="utf-8") as f:
                allowed = json.load(f)
        allowed[tool_name] = True
        with open(fallback_path, "w", encoding="utf-8") as f:
            json.dump(allowed, f)
    except Exception as e:
        logging.warning(f"Failed to write fallback state: {e}")


def execute_buddhi_read(
    filepath: Optional[str] = None,
    db_path: Optional[str] = None,
    mode: str = "auto",
    task_intent: Optional[str] = None,
    budget: int = 4000,
    query: Optional[str] = None,
) -> str:
    # ----------------------------------------------------
    # Case 1: Query (glob pattern / find_by_name)
    # ----------------------------------------------------
    if query:
        matches: List[str] = []
        source = "graph"

        # Try searching the SQLite graph database first
        if db_path and Path(db_path).exists():
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Convert glob pattern to SQL LIKE pattern
                sql_pattern = query.replace("*", "%").replace("?", "_")
                if "%" not in sql_pattern:
                    sql_pattern = f"%{sql_pattern}%"

                # 1. Match files by path
                cursor.execute("SELECT path FROM files WHERE path LIKE ?", (sql_pattern,))
                for row in cursor.fetchall():
                    matches.append(row[0])

                # 2. Match symbol/node names
                cursor.execute(
                    """
                    SELECT DISTINCT f.path 
                    FROM files f 
                    JOIN nodes n ON f.id = n.file_id 
                    WHERE n.name LIKE ?
                    """,
                    (sql_pattern,)
                )
                for row in cursor.fetchall():
                    if row[0] not in matches:
                        matches.append(row[0])

                conn.close()
            except sqlite3.Error as e:
                logging.warning(f"Error querying graph DB: {e}")

        # Try native glob fallback if database had no matches or failed
        if not matches:
            source = "native fallback"
            p = Path(".")
            glob_pattern = query if ("*" in query or "?" in query) else f"*{query}*"
            try:
                for path in p.rglob(glob_pattern):
                    if path.is_file():
                        parts = path.parts
                        if not any(ignored in parts for ignored in (".git", "node_modules", ".buddhi", ".venv", ".agents", "__pycache__")):
                            matches.append(str(path.as_posix()))
            except Exception as e:
                logging.warning(f"Native glob lookup failed: {e}")

        if matches:
            # Sort for determinism
            matches.sort()
            result = f"### Found {len(matches)} matching file(s) via {source}:\n"
            for m in matches:
                result += f"- {m}\n"
            return result
        else:
            # Let the agent know nothing was found and allow a native tool fallback in the gate_io hook
            _write_fallback_allowed("find_by_name")
            return f"Error: No files or symbols matching '{query}' found. (Native find_by_name is now unlocked as fallback)"

    # ----------------------------------------------------
    # Case 2: Filepath (view_file)
    # ----------------------------------------------------
    if not filepath:
        return "Error: Either 'filepath' or 'query' must be provided to buddhi_read."

    path = Path(filepath)
    if not path.exists() or not path.is_file():
        _write_fallback_allowed("view_file")
        return f"Error: Target file '{filepath}' does not exist or is not a file."
        
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read()
    except Exception as e:
        _write_fallback_allowed("view_file")
        return f"Error reading file '{filepath}': {e}"
        
    conn = None
    if db_path:
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_read_history (
                    filepath       TEXT NOT NULL,
                    mode           TEXT NOT NULL,
                    timestamp_micro INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        except sqlite3.Error as e:
            logging.warning(f"Error connecting to telemetry DB: {e}")

    try:
        # Phase 1: Bounce & State Verification
        tripped = False
        if conn:
            tripped = should_trip_circuit_breaker(conn, filepath, threshold=0.30)

        # Phase 2: Task-Aware Mode Resolution
        if tripped:
            logging.info(f"Circuit breaker tripped for {filepath}. Forcing full mode.")
            resolved_mode = "full"
        elif mode.lower() == "auto":
            resolved_mode = resolve_mode(filepath, task_intent)
        else:
            resolved_mode = mode.lower()

        # Log the event
        if conn:
            log_read_event(conn, filepath, resolved_mode)
    finally:
        if conn:
            conn.close()

    # Phase 3: AST Pruning & Entropy Filter
    processed_text = ""
    
    if resolved_mode == "signatures":
        processed_text = prune_signatures(filepath, raw_bytes)
        # Clean up empty lines left behind
        lines = [line for line in processed_text.splitlines() if line.strip()]
        processed_text = "\n".join(lines)
    elif resolved_mode == "map":
        processed_text = extract_map(filepath, raw_bytes)
    elif resolved_mode == "entropy":
        text = raw_bytes.decode("utf-8", errors="replace")
        filtered = filter_by_entropy(text.splitlines(), threshold=3.0)
        processed_text = "\n".join(filtered)
    else: # full
        processed_text = raw_bytes.decode("utf-8", errors="replace")
        
    # Phase 4: Layout Serialization & Token Budget Validation
    tokens = count_tokens(processed_text)
    
    if tokens > budget:
        logging.warning(f"Output for {filepath} exceeds budget ({tokens} > {budget} tokens). Falling back to map mode.")
        if resolved_mode != "map":
            processed_text = extract_map(filepath, raw_bytes)
            
    ext = path.suffix.lstrip(".")
    if not ext:
        ext = "txt"
        
    # Custom inline file-line annotations can be complex to rebuild perfectly after pruning, 
    # but the markdown structure is required.
    return f"```{ext}\n{processed_text}\n```"
