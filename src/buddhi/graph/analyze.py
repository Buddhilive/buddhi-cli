"""Topological graph analytics: god nodes, surprises, review questions, cycles, and stats."""

from __future__ import annotations

import collections
import sqlite3
from pathlib import Path
from typing import Any

from buddhi.graph.cache import get_git_head_sha
from buddhi.persist.sqlite_writer import get_db_capabilities

_BUILTIN_NOISE_LABELS = {
    "str",
    "int",
    "bool",
    "float",
    "dict",
    "list",
    "set",
    "tuple",
    "None",
    "Optional",
    "Any",
    "Union",
    "Path",
    "Callable",
    "Iterable",
    "Mapping",
    "Sequence",
    "Type",
    "Mock",
    "MagicMock",
    "pytest",
    "self",
    "this",
    "cls",
    "args",
    "kwargs",
    "object",
}


def get_god_nodes(conn: sqlite3.Connection, top_n: int = 10) -> list[dict[str, Any]]:
    """Rank highest-degree architectural symbol hubs, filtering noise."""
    query = """
    WITH degree_counts AS (
        SELECT node_id, COUNT(*) as deg FROM (
            SELECT source_id AS node_id FROM edges WHERE kind IN ('calls', 'inherits', 'imports') AND resolved = 1
            UNION ALL
            SELECT target_id AS node_id FROM edges WHERE kind IN ('calls', 'inherits', 'imports') AND resolved = 1
        )
        GROUP BY node_id
    )
    SELECT n.id, n.name, n.kind, n.file_path, n.community_id, d.deg
    FROM nodes n
    JOIN degree_counts d ON n.id = d.node_id
    WHERE n.external = 0 AND n.kind IN ('class', 'function', 'method')
    ORDER BY d.deg DESC
    LIMIT ?
    """
    cursor = conn.cursor()
    cursor.execute(query, (top_n * 2,))
    results: list[dict[str, Any]] = []
    for r in cursor.fetchall():
        name = r[1]
        if name in _BUILTIN_NOISE_LABELS:
            continue
        results.append(
            {
                "id": r[0],
                "name": name,
                "kind": r[2],
                "file_path": r[3],
                "community_id": r[4],
                "degree": r[5],
            }
        )
        if len(results) >= top_n:
            break
    return results


def get_surprising_connections(
    conn: sqlite3.Connection, top_n: int = 10
) -> list[dict[str, Any]]:
    """Rank edges by composite surprise score."""
    caps = get_db_capabilities(conn)
    conf_col = (
        "e.confidence" if caps["has_edge_confidence"] else "'EXTRACTED' AS confidence"
    )

    query = f"""
    SELECT
        e.source_id, e.target_id, e.kind, {conf_col},
        s.file_path AS s_file, s.community_id AS s_comm,
        t.file_path AS t_file, t.community_id AS t_comm,
        s.name AS s_name, t.name AS t_name
    FROM edges e
    JOIN nodes s ON e.source_id = s.id
    JOIN nodes t ON e.target_id = t.id
    WHERE e.kind IN ('calls', 'inherits') AND e.resolved = 1 AND s.external = 0 AND t.external = 0
    LIMIT 1000
    """
    cursor = conn.cursor()
    cursor.execute(query)

    scored: list[dict[str, Any]] = []
    for r in cursor.fetchall():
        (
            source_id,
            target_id,
            kind,
            confidence,
            s_file,
            s_comm,
            t_file,
            t_comm,
            s_name,
            t_name,
        ) = r
        score = 0.0

        # Cross-community bridge
        if s_comm is not None and t_comm is not None and s_comm != t_comm:
            score += 0.40

        # Cross top-level directory
        s_dir = (s_file or "").split("/")[0] if s_file else ""
        t_dir = (t_file or "").split("/")[0] if t_file else ""
        if s_dir and t_dir and s_dir != t_dir:
            score += 0.25

        # Confidence bonus
        if confidence == "AMBIGUOUS":
            score += 0.25
        elif confidence == "INFERRED":
            score += 0.15

        if score > 0.3:
            scored.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "kind": kind,
                    "confidence": confidence,
                    "source_name": s_name,
                    "target_name": t_name,
                    "source_file": s_file,
                    "target_file": t_file,
                    "surprise_score": round(score, 2),
                }
            )

    scored.sort(key=lambda x: -x["surprise_score"])
    return scored[:top_n]


def suggest_questions(conn: sqlite3.Connection, top_n: int = 7) -> list[dict[str, Any]]:
    """Synthesize architectural review questions across 5 diagnostic categories."""
    caps = get_db_capabilities(conn)
    questions: list[dict[str, Any]] = []

    # 1. Low cohesion communities
    if caps["has_communities"]:
        cur = conn.execute(
            "SELECT id, label, cohesion, node_count FROM communities WHERE cohesion < 0.15 AND node_count >= 5 ORDER BY cohesion ASC LIMIT 2"
        )
        for row in cur.fetchall():
            questions.append(
                {
                    "category": "low_cohesion",
                    "target": f"Community {row[0]} ({row[1]})",
                    "question": f"Community '{row[1]}' has low internal cohesion ({row[2]}). Should its {row[3]} components be decoupled into distinct modules?",
                }
            )

    # 2. Ambiguous edges
    if caps["has_edge_confidence"]:
        cur = conn.execute(
            "SELECT source_id, target_id, kind FROM edges WHERE confidence = 'AMBIGUOUS' LIMIT 2"
        )
        for row in cur.fetchall():
            questions.append(
                {
                    "category": "ambiguous_edge",
                    "target": f"{row[0]} -> {row[1]}",
                    "question": f"Edge {row[0]} -> {row[1]} ({row[2]}) is ambiguous. Is this dependency intended or an accidental name collision?",
                }
            )

    # 3. God nodes
    gods = get_god_nodes(conn, top_n=2)
    for g in gods:
        questions.append(
            {
                "category": "bridge_node",
                "target": g["id"],
                "question": f"Symbol '{g['name']}' in {g['file_path']} has high incident degree ({g['degree']}). Does it represent a god object that warrants refactoring?",
            }
        )

    return questions[:top_n]


def find_shortest_path(
    conn: sqlite3.Connection, source_query: str, target_query: str, max_hops: int = 8
) -> dict[str, Any]:
    """Find the shortest relational path between two symbols with candidate disambiguation."""

    def resolve_symbol(q: str) -> tuple[str | None, list[str]]:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, file_path FROM nodes WHERE id = ? OR name = ? OR qualified_name = ?",
            (q, q, q),
        )
        rows = cur.fetchall()
        if not rows:
            cur.execute(
                "SELECT id, name, file_path FROM nodes WHERE name LIKE ? LIMIT 5",
                (f"%{q}%",),
            )
            rows = cur.fetchall()
        if len(rows) == 1:
            return rows[0][0], []
        if len(rows) > 1:
            return None, [f"{r[0]} ({r[2]})" for r in rows]
        return None, []

    s_id, s_disambig = resolve_symbol(source_query)
    t_id, t_disambig = resolve_symbol(target_query)

    if s_disambig:
        return {"error": "source_disambiguation_required", "candidates": s_disambig}
    if t_disambig:
        return {"error": "target_disambiguation_required", "candidates": t_disambig}
    if not s_id or not t_id:
        return {
            "error": "symbol_not_found",
            "source": s_id or source_query,
            "target": t_id or target_query,
        }

    # BFS
    queue = collections.deque([(s_id, [s_id])])
    visited = {s_id}

    while queue:
        curr, path = queue.popleft()
        if curr == t_id:
            return {"found": True, "hops": len(path) - 1, "path": path}
        if len(path) - 1 >= max_hops:
            continue

        cur = conn.cursor()
        cur.execute(
            "SELECT target_id FROM edges WHERE source_id = ? AND kind IN ('calls', 'inherits', 'imports') AND resolved = 1",
            (curr,),
        )
        for (nxt,) in cur.fetchall():
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))

    return {"found": False, "hops": -1, "path": []}


def find_import_cycles(
    conn: sqlite3.Connection, max_cycles: int = 50
) -> list[list[str]]:
    """Detect circular file-level IMPORTS chains."""
    cur = conn.cursor()
    cur.execute(
        "SELECT source_id, target_id FROM edges WHERE kind = 'imports' AND resolved = 1"
    )
    adj: dict[str, list[str]] = collections.defaultdict(list)
    for src, tgt in cur.fetchall():
        if src.startswith("file:") and tgt.startswith("file:"):
            adj[src].append(tgt)

    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: list[str] = []
    on_stack: set[str] = set()

    def dfs(node: str) -> None:
        if len(cycles) >= max_cycles:
            return
        visited.add(node)
        stack.append(node)
        on_stack.add(node)

        for neighbor in adj.get(node, []):
            if neighbor in on_stack:
                idx = stack.index(neighbor)
                cycle = stack[idx:] + [neighbor]
                cycles.append([c.removeprefix("file:") for c in cycle])
                if len(cycles) >= max_cycles:
                    return
            elif neighbor not in visited:
                dfs(neighbor)

        stack.pop()
        on_stack.remove(node)

    for n in sorted(adj.keys()):
        if n not in visited:
            dfs(n)

    return cycles


def get_community_detail(conn: sqlite3.Connection, community_id: int) -> dict[str, Any]:
    """Return member nodes and community info."""
    caps = get_db_capabilities(conn)
    comm_info: dict[str, Any] = {"id": community_id}
    if caps["has_communities"]:
        row = conn.execute(
            "SELECT label, node_count, cohesion, hub_node_id FROM communities WHERE id = ?",
            (community_id,),
        ).fetchone()
        if row:
            comm_info.update(
                {
                    "label": row[0],
                    "node_count": row[1],
                    "cohesion": row[2],
                    "hub_node_id": row[3],
                }
            )

    members = [
        {"id": r[0], "name": r[1], "kind": r[2], "file_path": r[3]}
        for r in conn.execute(
            "SELECT id, name, kind, file_path FROM nodes WHERE community_id = ?",
            (community_id,),
        ).fetchall()
    ]
    comm_info["members"] = members
    return comm_info


def get_graph_stats(conn: sqlite3.Connection, root_path: Path) -> dict[str, Any]:
    """Return node/edge counts, confidence breakdown, and git staleness."""
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    caps = get_db_capabilities(conn)

    built_commit = meta.get("built_at_commit") or "unknown"
    current_head = get_git_head_sha(root_path) or "unknown"

    stats: dict[str, Any] = {
        "nodes": int(meta.get("node_count", 0)),
        "edges": int(meta.get("edge_count", 0)),
        "communities": int(meta.get("community_count", 0)),
        "built_at_commit": built_commit,
        "current_git_head": current_head,
        "is_stale": (
            built_commit != "unknown"
            and current_head != "unknown"
            and built_commit != current_head
        ),
    }

    if caps["has_edge_confidence"]:
        conf_counts = dict(
            conn.execute(
                "SELECT confidence, COUNT(*) FROM edges GROUP BY confidence"
            ).fetchall()
        )
        stats["confidence_breakdown"] = conf_counts

    return stats
