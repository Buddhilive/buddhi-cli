from __future__ import annotations

import logging
from pathlib import Path
import sqlite3

from buddhi.mcp.compression.ast_pruner import extract_map, prune_signatures
from buddhi.mcp.compression.classifier import resolve_mode
from buddhi.mcp.compression.entropy import count_tokens, filter_by_entropy


def execute_buddhi_read(
    filepath: str | None = None,
    db_path: str | None = None,
    mode: str = "auto",
    task_intent: str | None = None,
    budget: int = 4000,
    query: str | None = None,
) -> str:
    # ----------------------------------------------------
    # Case 1: Query (glob pattern / symbol search)
    # ----------------------------------------------------
    if query:
        matches: list[str] = []
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
                cursor.execute(
                    "SELECT DISTINCT file_path FROM nodes WHERE file_path IS NOT NULL AND file_path LIKE ?",
                    (sql_pattern,),
                )
                for row in cursor.fetchall():
                    if row[0]:
                        matches.append(row[0])

                # 2. Match symbol/node names
                cursor.execute(
                    "SELECT DISTINCT file_path FROM nodes WHERE file_path IS NOT NULL AND (name LIKE ? OR qualified_name LIKE ?)",
                    (sql_pattern, sql_pattern),
                )
                for row in cursor.fetchall():
                    if row[0] and row[0] not in matches:
                        matches.append(row[0])

                conn.close()
            except sqlite3.Error as e:
                logging.warning("Error querying graph DB: %s", e)

        # Try native glob fallback if database had no matches or failed
        if not matches:
            source = "native fallback"
            p = Path(".")
            glob_pattern = query if ("*" in query or "?" in query) else f"*{query}*"
            try:
                for path in p.rglob(glob_pattern):
                    if path.is_file():
                        parts = path.parts
                        if not any(
                            ignored in parts
                            for ignored in (
                                ".git",
                                "node_modules",
                                ".buddhi",
                                ".venv",
                                "venv",
                                ".agents",
                                "__pycache__",
                            )
                        ):
                            matches.append(str(path.as_posix()))
            except Exception as e:
                logging.warning("Native glob lookup failed: %s", e)

        if matches:
            matches.sort()
            result = f"### Found {len(matches)} matching file(s) via {source}:\n"
            for m in matches:
                result += f"- {m}\n"
            return result

        return f"Error: No files or symbols matching '{query}' found in graph or workspace."

    # ----------------------------------------------------
    # Case 2: Filepath
    # ----------------------------------------------------
    if not filepath:
        return "Error: Either 'filepath' or 'query' must be provided to buddhi_read."

    path = Path(filepath)
    if not path.exists() or not path.is_file():
        return f"Error: Target file '{filepath}' does not exist or is not a file."

    try:
        raw_bytes = path.read_bytes()
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"

    # Mode Resolution
    if mode.lower() == "auto":
        resolved_mode = resolve_mode(filepath, task_intent)
    else:
        resolved_mode = mode.lower()

    # AST Pruning & Entropy Filter
    processed_text = ""

    if resolved_mode == "signatures":
        processed_text = prune_signatures(filepath, raw_bytes)
        lines = [line for line in processed_text.splitlines() if line.strip()]
        processed_text = "\n".join(lines)
    elif resolved_mode == "map":
        processed_text = extract_map(filepath, raw_bytes)
    elif resolved_mode == "entropy":
        text = raw_bytes.decode("utf-8", errors="replace")
        filtered = filter_by_entropy(text.splitlines(), threshold=3.0)
        processed_text = "\n".join(filtered)
    else:  # full
        processed_text = raw_bytes.decode("utf-8", errors="replace")

    # Layout Serialization & Token Budget Validation
    tokens = count_tokens(processed_text)

    if tokens > budget:
        logging.warning(
            "Output for %s exceeds budget (%d > %d tokens). Falling back to map mode.",
            filepath,
            tokens,
            budget,
        )
        if resolved_mode != "map":
            processed_text = extract_map(filepath, raw_bytes)

    ext = path.suffix.lstrip(".")
    if not ext:
        ext = "txt"

    return f"```{ext}\n{processed_text}\n```"
