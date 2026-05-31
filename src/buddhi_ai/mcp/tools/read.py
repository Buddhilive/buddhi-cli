import sqlite3
import logging
from pathlib import Path
from typing import Optional

from buddhi_ai.mcp.compression.telemetry import log_read_event, should_trip_circuit_breaker
from buddhi_ai.mcp.compression.classifier import resolve_mode
from buddhi_ai.mcp.compression.entropy import filter_by_entropy, count_tokens
from buddhi_ai.mcp.compression.ast_pruner import prune_signatures, extract_map


def execute_buddhi_read(
    filepath: str,
    db_path: Optional[str] = None,
    mode: str = "auto",
    task_intent: Optional[str] = None,
    budget: int = 4000
) -> str:
    path = Path(filepath)
    if not path.exists() or not path.is_file():
        return f"Error: Target file '{filepath}' does not exist or is not a file."
        
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read()
    except Exception as e:
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
