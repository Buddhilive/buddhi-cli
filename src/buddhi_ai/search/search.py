"""
Core search pipeline orchestrator.

Executes the 4-phase topology-driven retrieval pipeline:
    Phase 1: Lexical Anchor Identification (BM25 via FTS5)
    Phase 2: Boundary-Node Cluster Expansion (Leiden communities + 1-hop bridges)
    Phase 3: Content Pruning & Mode-Aware Filtering
    Phase 4: Attention Layout (U-Curve Matrix)
    Phase 5: Budget Overflow Compression (optional)
"""
import sqlite3
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

from buddhi_ai.search.compressor import compress_to_budget
from buddhi_ai.search.formatter import (
    SearchResult,
    serialize_context,
    u_curve_sort,
)
from buddhi_ai.search.query_expansion import build_fts_query, expand_query

# Edge weight threshold for bridge expansion
BRIDGE_WEIGHT_THRESHOLD = 3.0


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


def _native_grep_search(query: str) -> str:
    """Fuzzy/regex search files recursively in the workspace as a fallback."""
    matches = []
    p = Path(".")
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except Exception:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    try:
        for path in p.rglob("*"):
            if path.is_file():
                parts = path.parts
                if not any(ignored in parts for ignored in (".git", "node_modules", ".buddhi", ".venv", ".agents", "__pycache__")):
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            for idx, line in enumerate(f, 1):
                                if pattern.search(line):
                                    matches.append(f"{path.as_posix()}:{idx}: {line.strip()}")
                                    if len(matches) >= 50:
                                        break
                    except Exception:
                        pass
            if len(matches) >= 50:
                break
    except Exception:
        pass

    if matches:
        return "### Native Grep Fallback Matches:\n" + "\n".join(matches)
    return ""


def buddhi_search(
    query: str,
    db_path: str,
    top_n: int = 3,
    mode: str = "full",
    include_bridges: bool = True,
    budget: int = 0,
    return_stats: bool = False,
) -> str | Tuple[str, int]:
    """Search the code graph and return context-optimized results.

    Args:
        query: The search query string.
        db_path: Path to the .buddhi/graph.db SQLite database.
        top_n: Number of top lexical anchors to retrieve (default: 3).
        mode: Output mode — "full", "signatures", or "map".
        include_bridges: Whether to include 1-hop bridge nodes from
                         external communities.
        budget: Maximum character count for output. 0 = unbounded.
        return_stats: If True, return (output_string, raw_token_count).

    Returns:
        Serialized context string with delimiter boundaries, optimized
        for LLM attention via U-Curve positional layout.
    """
    from buddhi_ai.metrics.logger import MetricsLogger

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Phase 1: Lexical Anchor Identification
        anchor_ids, community_ids = _phase1_lexical_anchors(conn, query, top_n)

        # Phase 1b: Fallback if zero hits
        if not anchor_ids:
            anchor_ids, community_ids = _phase1b_fallback(conn, query, top_n)

        # If still nothing: try native fallback
        if not anchor_ids:
            output = _native_grep_search(query)
            if output:
                return (output, MetricsLogger.count_tokens(output)) if return_stats else output
            
            # If native also has nothing, allow native grep_search and return error
            _write_fallback_allowed("grep_search")
            err_msg = f"Error: No results found for query '{query}' in graph or workspace. (Native grep_search is now unlocked as fallback)"
            return (err_msg, MetricsLogger.count_tokens(err_msg)) if return_stats else err_msg

        # Phase 2: Boundary-Node Cluster Expansion
        results = _phase2_cluster_expansion(
            conn, anchor_ids, community_ids, include_bridges
        )

        # Phase 3: Apply content mode to all results
        for result in results:
            result.mode = mode

        # Calculate raw token count before any budgeting/compression
        raw_token_count = 0
        if return_stats:
            # We use full mode to calculate the maximum potential token cost 
            # if buddhi wasn't being used
            raw_output = serialize_context(results)
            raw_token_count = MetricsLogger.count_tokens(raw_output)

        # Phase 4: Attention Layout (U-Curve)
        results = u_curve_sort(results)

        # Serialize
        output = serialize_context(results)

        # Phase 5: Budget Overflow Compression
        if budget > 0 and len(output) > budget:
            results = compress_to_budget(results, budget, db_path)
            # Re-sort after compression may have changed the node list
            results = u_curve_sort(results)
            output = serialize_context(results)

        return (output, raw_token_count) if return_stats else output

    finally:
        conn.close()


def _phase1_lexical_anchors(
    conn: sqlite3.Connection,
    query: str,
    top_n: int,
) -> Tuple[List[int], Set[int]]:
    """Phase 1: Run FTS5 BM25 match to find lexical anchor nodes.

    Returns:
        Tuple of (anchor_node_ids, community_ids).
    """
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT rowid, rank FROM nodes_fts WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, top_n),
        )
    except sqlite3.OperationalError:
        # FTS5 query syntax error (e.g., special characters)
        return [], set()

    rows = cursor.fetchall()
    if not rows:
        return [], set()

    anchor_ids = [row["rowid"] for row in rows]

    # Resolve community_ids
    placeholders = ",".join("?" for _ in anchor_ids)
    cursor.execute(
        f"SELECT id, community_id FROM nodes WHERE id IN ({placeholders})",
        anchor_ids,
    )
    community_ids: Set[int] = set()
    for row in cursor.fetchall():
        cid = row["community_id"]
        if cid is not None:
            community_ids.add(cid)

    return anchor_ids, community_ids


def _phase1b_fallback(
    conn: sqlite3.Connection,
    query: str,
    top_n: int,
) -> Tuple[List[int], Set[int]]:
    """Phase 1b: Zero-hit fallback with query expansion.

    Splits the query on camelCase/snake_case boundaries and re-runs
    FTS5 with OR-expanded terms.
    """
    expanded_terms = expand_query(query)
    if not expanded_terms:
        return [], set()

    fts_query = build_fts_query(expanded_terms)
    if not fts_query:
        return [], set()

    return _phase1_lexical_anchors(conn, fts_query, top_n)


def _generate_file_map(conn: sqlite3.Connection) -> str:
    """Generate a shallow directory/file-level map as ultimate fallback.

    Returns a compact listing of all indexed files.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM files ORDER BY path")
    rows = cursor.fetchall()

    if not rows:
        return "No files indexed. Run `buddhi init` first."

    lines = ["--- FILE MAP (no matching symbols found) ---"]
    for row in rows:
        lines.append(f"  {row['path']}")
    lines.append("--- END FILE MAP ---")
    return "\n".join(lines)


def _phase2_cluster_expansion(
    conn: sqlite3.Connection,
    anchor_ids: List[int],
    community_ids: Set[int],
    include_bridges: bool,
) -> List[SearchResult]:
    """Phase 2: Gather primary community + optional 1-hop bridge nodes.

    Tags each node with its salience tier:
        - anchor: exact FTS match
        - community: same community_id as an anchor
        - bridge: 1-hop external node with strong edge
    """
    cursor = conn.cursor()
    anchor_set = set(anchor_ids)

    # Primary gathering: all nodes in the anchor communities
    results_by_id: Dict[int, SearchResult] = {}

    if community_ids:
        placeholders = ",".join("?" for _ in community_ids)
        cursor.execute(
            f"""
            SELECT n.id, n.name, n.node_type, n.content, n.start_line, n.end_line,
                   n.community_id, f.path
            FROM nodes n
            LEFT JOIN files f ON n.file_id = f.id
            WHERE n.community_id IN ({placeholders})
            """,
            list(community_ids),
        )
        for row in cursor.fetchall():
            node_id = row["id"]
            tier = "anchor" if node_id in anchor_set else "community"
            results_by_id[node_id] = SearchResult(
                node_id=node_id,
                name=row["name"] or "anonymous",
                file_path=row["path"] or "",
                content=row["content"] or "",
                start_line=row["start_line"] or 0,
                end_line=row["end_line"] or 0,
                community_id=row["community_id"] or 0,
                salience_tier=tier,
                node_type=row["node_type"] or "",
            )

    # Ensure anchor nodes are always included even if community_id was NULL
    for aid in anchor_ids:
        if aid not in results_by_id:
            cursor.execute(
                """
                SELECT n.id, n.name, n.node_type, n.content, n.start_line, n.end_line,
                       n.community_id, f.path
                FROM nodes n
                LEFT JOIN files f ON n.file_id = f.id
                WHERE n.id = ?
                """,
                (aid,),
            )
            row = cursor.fetchone()
            if row:
                results_by_id[aid] = SearchResult(
                    node_id=row["id"],
                    name=row["name"] or "anonymous",
                    file_path=row["path"] or "",
                    content=row["content"] or "",
                    start_line=row["start_line"] or 0,
                    end_line=row["end_line"] or 0,
                    community_id=row["community_id"] or 0,
                    salience_tier="anchor",
                    node_type=row["node_type"] or "",
                )

    # Bridge traversal: 1-hop outbound from primary community nodes
    if include_bridges and results_by_id:
        primary_ids = list(results_by_id.keys())
        placeholders = ",".join("?" for _ in primary_ids)

        cursor.execute(
            f"""
            SELECT e.target_id, e.weight
            FROM edges e
            WHERE e.source_id IN ({placeholders})
              AND e.weight >= ?
            """,
            primary_ids + [BRIDGE_WEIGHT_THRESHOLD],
        )

        bridge_candidates: Dict[int, float] = {}
        for row in cursor.fetchall():
            target_id = row["target_id"]
            weight = row["weight"]
            # Only pull if it's in a different community (external)
            if target_id not in results_by_id:
                bridge_candidates[target_id] = max(
                    bridge_candidates.get(target_id, 0.0), weight
                )

        # Also check inbound edges (target is in primary, source is external)
        cursor.execute(
            f"""
            SELECT e.source_id, e.weight
            FROM edges e
            WHERE e.target_id IN ({placeholders})
              AND e.weight >= ?
            """,
            primary_ids + [BRIDGE_WEIGHT_THRESHOLD],
        )
        for row in cursor.fetchall():
            source_id = row["source_id"]
            weight = row["weight"]
            if source_id not in results_by_id:
                bridge_candidates[source_id] = max(
                    bridge_candidates.get(source_id, 0.0), weight
                )

        # Fetch bridge node details
        if bridge_candidates:
            bridge_ids = list(bridge_candidates.keys())
            placeholders = ",".join("?" for _ in bridge_ids)
            cursor.execute(
                f"""
                SELECT n.id, n.name, n.node_type, n.content, n.start_line, n.end_line,
                       n.community_id, f.path
                FROM nodes n
                LEFT JOIN files f ON n.file_id = f.id
                WHERE n.id IN ({placeholders})
                """,
                bridge_ids,
            )
            for row in cursor.fetchall():
                node_id = row["id"]
                results_by_id[node_id] = SearchResult(
                    node_id=node_id,
                    name=row["name"] or "anonymous",
                    file_path=row["path"] or "",
                    content=row["content"] or "",
                    start_line=row["start_line"] or 0,
                    end_line=row["end_line"] or 0,
                    community_id=row["community_id"] or 0,
                    salience_tier="bridge",
                    node_type=row["node_type"] or "",
                    edge_weight_sum=bridge_candidates.get(node_id, 0.0),
                )

    return list(results_by_id.values())
