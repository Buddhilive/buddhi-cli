from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re
import sqlite3

from buddhi.mcp.compression.entropy import calculate_entropy, count_tokens

_ENTROPY_THRESHOLD = 3.0


@dataclass
class SearchResult:
    """A single node in the search result set."""

    node_id: str
    name: str
    file_path: str
    content: str
    signature: str
    start_line: int
    end_line: int
    community_id: int
    salience_tier: str  # "anchor" | "community" | "bridge"
    node_type: str
    edge_count: int = 0
    mode: str = "full"


def expand_query(query: str) -> list[str]:
    """Split a query string into component tokens.

    Handles camelCase, PascalCase, snake_case, and space-separated terms.
    Filters out tokens shorter than 2 characters.
    """
    tokens: list[str] = []

    for word in query.split():
        parts = word.split("_")
        for part in parts:
            if not part:
                continue
            camel_parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", part)
            camel_parts = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", camel_parts)
            tokens.extend(camel_parts.split())

    return [t for t in tokens if len(t) >= 2]


def filter_low_entropy_lines(content: str, threshold: float = _ENTROPY_THRESHOLD) -> str:
    """Remove lines with Shannon entropy below the threshold."""
    if not content:
        return content

    lines = content.splitlines()
    filtered: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            filtered.append(line)
            continue

        entropy = calculate_entropy(stripped)
        if entropy >= threshold:
            filtered.append(line)

    return "\n".join(filtered)


def extract_signature(content: str, signature: str, node_type: str) -> str:
    """Extract or return signature and docstring from definition."""
    if signature and signature.strip():
        return signature.strip()

    if not content:
        return content

    lines = content.splitlines()
    nt = node_type.lower()
    if "function" in nt or "method" in nt or "class" in nt:
        sig_lines: list[str] = []
        found_colon = False
        for line in lines:
            sig_lines.append(line)
            if not found_colon and (line.rstrip().endswith(":") or line.rstrip().endswith("{")):
                found_colon = True
                continue
            if found_colon:
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith("/*"):
                    sig_lines.append(line)
                    if (
                        stripped.count('"""') >= 2
                        or stripped.count("'''") >= 2
                        or "*/" in stripped
                    ):
                        break
                    for remaining in lines[len(sig_lines) :]:
                        sig_lines.append(remaining)
                        if '"""' in remaining or "'''" in remaining or "*/" in remaining:
                            break
                break

        if sig_lines:
            return "\n".join(sig_lines)

    return lines[0] if lines else content


def extract_map_entry(result: SearchResult) -> str:
    """Return a compact one-liner for map mode."""
    loc = f"{result.file_path}:L{result.start_line}-L{result.end_line}" if result.start_line else result.file_path
    return f"{result.name} ({result.node_type}) — {loc}"


def render_content(result: SearchResult) -> str:
    """Render node content according to its current mode."""
    if result.mode == "map":
        return extract_map_entry(result)

    if result.mode == "signatures":
        content = extract_signature(result.content, result.signature, result.node_type)
    else:
        content = result.content or result.signature

    return filter_low_entropy_lines(content)


def u_curve_sort(nodes: list[SearchResult]) -> list[SearchResult]:
    """Reorder nodes using U-Curve positional optimization.

    Layout:
        Top:    anchor nodes (highest salience)
        Middle: bridge nodes (attention dead zone)
        Bottom: community structural boundaries
    """
    if not nodes:
        return nodes

    anchors = [n for n in nodes if n.salience_tier == "anchor"]
    community = [n for n in nodes if n.salience_tier == "community"]
    bridges = [n for n in nodes if n.salience_tier == "bridge"]

    return anchors + bridges + community


def serialize_context(nodes: list[SearchResult]) -> str:
    """Serialize search results into delimited text with boundary markers."""
    if not nodes:
        return ""

    blocks: list[str] = []
    for result in nodes:
        header = f"--- START SYMBOL: {result.file_path}::{result.name} (L{result.start_line}-L{result.end_line}) ---"
        content = render_content(result)
        footer = "--- END SYMBOL ---"
        blocks.append(f"{header}\n{content}\n{footer}")

    return "\n\n".join(blocks)


def _tier1_strip_bridges(nodes: list[SearchResult]) -> list[SearchResult]:
    return [n for n in nodes if n.salience_tier != "bridge"]


def _tier2_degrade_modes(nodes: list[SearchResult]) -> list[SearchResult]:
    degraded = []
    for node in nodes:
        new_node = SearchResult(
            node_id=node.node_id,
            name=node.name,
            file_path=node.file_path,
            content=node.content,
            signature=node.signature,
            start_line=node.start_line,
            end_line=node.end_line,
            community_id=node.community_id,
            salience_tier=node.salience_tier,
            node_type=node.node_type,
            edge_count=node.edge_count,
            mode=node.mode,
        )
        if new_node.mode == "full":
            new_node.mode = "signatures"
        elif new_node.mode == "signatures":
            new_node.mode = "map"
        degraded.append(new_node)
    return degraded


def _tier3_drop_low_weight(nodes: list[SearchResult]) -> list[SearchResult]:
    if len(nodes) <= 1:
        return nodes

    anchors = [n for n in nodes if n.salience_tier == "anchor"]
    non_anchors = [n for n in nodes if n.salience_tier != "anchor"]
    non_anchors.sort(key=lambda n: n.edge_count, reverse=True)

    keep_count = max(1, len(non_anchors) // 2)
    return anchors + non_anchors[:keep_count]


def compress_to_budget(nodes: list[SearchResult], budget: int) -> list[SearchResult]:
    output = serialize_context(nodes)
    if count_tokens(output) <= budget:
        return nodes

    # Tier 1: Strip bridges
    nodes = _tier1_strip_bridges(nodes)
    output = serialize_context(nodes)
    if count_tokens(output) <= budget:
        return nodes

    # Tier 2: Degrade modes
    nodes = _tier2_degrade_modes(nodes)
    output = serialize_context(nodes)
    if count_tokens(output) <= budget:
        return nodes

    # Second degradation pass (signatures -> map)
    nodes = _tier2_degrade_modes(nodes)
    output = serialize_context(nodes)
    if count_tokens(output) <= budget:
        return nodes

    # Tier 3: Drop low connectivity nodes
    for _ in range(5):
        prev_count = len(nodes)
        nodes = _tier3_drop_low_weight(nodes)
        output = serialize_context(nodes)
        if count_tokens(output) <= budget or len(nodes) == prev_count:
            break

    return nodes


def _native_grep_search(query: str) -> str:
    """Fuzzy/regex search files recursively in the workspace as a fallback."""
    matches: list[str] = []
    p = Path(".")
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except Exception:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    try:
        for path in p.rglob("*"):
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
                    try:
                        with path.open("r", encoding="utf-8", errors="replace") as f:
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
        return "### [fallback: native grep] Native Grep Fallback Matches:\n" + "\n".join(matches)
    return ""


def _direct_sql_fallback(conn: sqlite3.Connection, query: str, top_n: int = 10) -> list[SearchResult]:
    """Graceful fallback querying SQLite nodes directly via LIKE."""
    cursor = conn.cursor()
    sql_pattern = f"%{query}%"
    cursor.execute(
        """
        SELECT id, name, kind, file_path, start_line, end_line, signature, snippet, community_id
        FROM nodes
        WHERE external = 0 AND (name LIKE ? OR qualified_name LIKE ? OR snippet LIKE ?)
        LIMIT ?
        """,
        (sql_pattern, sql_pattern, sql_pattern, top_n),
    )
    rows = cursor.fetchall()
    results: list[SearchResult] = []
    for r in rows:
        results.append(
            SearchResult(
                node_id=r[0],
                name=r[1] or "",
                file_path=r[3] or "",
                content=r[7] or "",
                signature=r[6] or "",
                start_line=r[4] or 0,
                end_line=r[5] or 0,
                community_id=r[8] or 0,
                salience_tier="anchor",
                node_type=r[2] or "",
            )
        )
    return results


def execute_buddhi_search(
    query: str,
    db_path: str,
    top_n: int = 3,
    mode: str = "full",
    include_bridges: bool = True,
    budget: int = 8000,
) -> str:
    """Search the codebase using Buddhi's topology-driven retrieval pipeline with graceful fallbacks."""
    if not Path(db_path).exists():
        # Graph DB not found -> fallback to native grep
        output = _native_grep_search(query)
        if output:
            return output
        return f"Error: Buddhi database not found at '{db_path}' and no native matches found. Please run `buddhi init` first."

    conn = sqlite3.connect(db_path)
    try:
        # Phase 1: Lexical Anchor Detection
        cursor = conn.cursor()
        expanded_terms = expand_query(query)
        search_terms = [query] + [t for t in expanded_terms if t.lower() != query.lower()]

        anchor_nodes: dict[str, SearchResult] = {}
        anchor_communities: set[int] = set()

        for term in search_terms:
            sql_pattern = f"%{term}%"
            cursor.execute(
                """
                SELECT id, name, kind, file_path, start_line, end_line, signature, snippet, community_id
                FROM nodes
                WHERE external = 0 AND (name LIKE ? OR qualified_name LIKE ?)
                LIMIT ?
                """,
                (sql_pattern, sql_pattern, top_n),
            )
            for r in cursor.fetchall():
                node_id = r[0]
                if node_id not in anchor_nodes:
                    comm_id = r[8] if r[8] is not None else 0
                    if comm_id:
                        anchor_communities.add(comm_id)
                    anchor_nodes[node_id] = SearchResult(
                        node_id=node_id,
                        name=r[1] or "",
                        file_path=r[3] or "",
                        content=r[7] or "",
                        signature=r[6] or "",
                        start_line=r[4] or 0,
                        end_line=r[5] or 0,
                        community_id=comm_id,
                        salience_tier="anchor",
                        node_type=r[2] or "",
                        mode=mode,
                    )
                if len(anchor_nodes) >= top_n:
                    break
            if len(anchor_nodes) >= top_n:
                break

        # Fallback Phase 1b: If no anchors on name/qual, search snippet
        if not anchor_nodes:
            cursor.execute(
                """
                SELECT id, name, kind, file_path, start_line, end_line, signature, snippet, community_id
                FROM nodes
                WHERE external = 0 AND snippet LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", top_n),
            )
            for r in cursor.fetchall():
                node_id = r[0]
                comm_id = r[8] if r[8] is not None else 0
                if comm_id:
                    anchor_communities.add(comm_id)
                anchor_nodes[node_id] = SearchResult(
                    node_id=node_id,
                    name=r[1] or "",
                    file_path=r[3] or "",
                    content=r[7] or "",
                    signature=r[6] or "",
                    start_line=r[4] or 0,
                    end_line=r[5] or 0,
                    community_id=comm_id,
                    salience_tier="anchor",
                    node_type=r[2] or "",
                    mode=mode,
                )

        # Fallback to Direct SQL if still no anchors
        if not anchor_nodes:
            sql_fallback_results = _direct_sql_fallback(conn, query, top_n=top_n * 2)
            if sql_fallback_results:
                for res in sql_fallback_results:
                    res.mode = mode
                serialized = serialize_context(sql_fallback_results)
                return f"### [fallback: direct SQL]\n{serialized}"

            # Fallback to Native Grep
            grep_output = _native_grep_search(query)
            if grep_output:
                return grep_output

            return f"Error: No results found for query '{query}' in graph or workspace."

        # Phase 2: Community Cluster Expansion
        results_by_id: dict[str, SearchResult] = dict(anchor_nodes)

        if anchor_communities:
            placeholders = ",".join("?" for _ in anchor_communities)
            cursor.execute(
                f"""
                SELECT id, name, kind, file_path, start_line, end_line, signature, snippet, community_id
                FROM nodes
                WHERE external = 0 AND community_id IN ({placeholders})
                """,
                list(anchor_communities),
            )
            for r in cursor.fetchall():
                node_id = r[0]
                if node_id not in results_by_id:
                    results_by_id[node_id] = SearchResult(
                        node_id=node_id,
                        name=r[1] or "",
                        file_path=r[3] or "",
                        content=r[7] or "",
                        signature=r[6] or "",
                        start_line=r[4] or 0,
                        end_line=r[5] or 0,
                        community_id=r[8] or 0,
                        salience_tier="community",
                        node_type=r[2] or "",
                        mode=mode,
                    )

        # 1-Hop Bridges & Edge Connectivity Weighting
        try:
            if include_bridges and results_by_id:
                primary_ids = list(results_by_id.keys())
                placeholders = ",".join("?" for _ in primary_ids)
                cursor.execute(
                    f"""
                    SELECT target_id FROM edges WHERE source_id IN ({placeholders})
                    UNION
                    SELECT source_id FROM edges WHERE target_id IN ({placeholders})
                    """,
                    primary_ids + primary_ids,
                )
                bridge_ids = [row[0] for row in cursor.fetchall() if row[0] not in results_by_id]
                if bridge_ids:
                    b_placeholders = ",".join("?" for _ in bridge_ids[:20])
                    cursor.execute(
                        f"""
                        SELECT id, name, kind, file_path, start_line, end_line, signature, snippet, community_id
                        FROM nodes
                        WHERE external = 0 AND id IN ({b_placeholders})
                        """,
                        bridge_ids[:20],
                    )
                    for r in cursor.fetchall():
                        node_id = r[0]
                        results_by_id[node_id] = SearchResult(
                            node_id=node_id,
                            name=r[1] or "",
                            file_path=r[3] or "",
                            content=r[7] or "",
                            signature=r[6] or "",
                            start_line=r[4] or 0,
                            end_line=r[5] or 0,
                            community_id=r[8] or 0,
                            salience_tier="bridge",
                            node_type=r[2] or "",
                            mode=mode,
                        )

            # Count incident edges for connectivity weighting
            all_ids = list(results_by_id.keys())
            if all_ids:
                placeholders = ",".join("?" for _ in all_ids)
                cursor.execute(
                    f"""
                    SELECT source_id, COUNT(*) FROM edges WHERE source_id IN ({placeholders}) GROUP BY source_id
                    """,
                    all_ids,
                )
                for sid, count in cursor.fetchall():
                    if sid in results_by_id:
                        results_by_id[sid].edge_count += count

                cursor.execute(
                    f"""
                    SELECT target_id, COUNT(*) FROM edges WHERE target_id IN ({placeholders}) GROUP BY target_id
                    """,
                    all_ids,
                )
                for tid, count in cursor.fetchall():
                    if tid in results_by_id:
                        results_by_id[tid].edge_count += count
        except sqlite3.OperationalError as edge_err:
            logging.debug("Edges table not queried: %s", edge_err)

        results = list(results_by_id.values())

        # Phase 3: U-Curve Layout
        results = u_curve_sort(results)

        # Phase 4: Budget Compression
        if budget > 0:
            results = compress_to_budget(results, budget)
            results = u_curve_sort(results)

        return serialize_context(results)

    except Exception as e:
        logging.exception("Error executing search: %s", e)
        return f"Error executing search: {e}"
    finally:
        conn.close()
