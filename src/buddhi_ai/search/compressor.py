"""
Budget overflow compression engine.

Implements 3-tier progressive compression to fit search results
within a character budget:
    Tier 1: Strip 1-hop bridge nodes from external communities
    Tier 2: Degrade internal resolution (full → signatures → map)
    Tier 3: Drop nodes with lowest degree of connectivity
"""
import sqlite3
from typing import Dict, List

from buddhi_ai.search.formatter import SearchResult, serialize_context


def calculate_node_weights(node_ids: List[int], db_path: str) -> Dict[int, float]:
    """Query edges table to compute sum of incident edge weights per node.

    Used by Tier 3 to rank nodes by graph importance.
    """
    if not node_ids:
        return {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    weights: Dict[int, float] = {nid: 0.0 for nid in node_ids}

    placeholders = ",".join("?" for _ in node_ids)
    cursor.execute(
        f"SELECT source_id, weight FROM edges WHERE source_id IN ({placeholders})",
        node_ids,
    )
    for source_id, weight in cursor.fetchall():
        weights[source_id] += weight

    cursor.execute(
        f"SELECT target_id, weight FROM edges WHERE target_id IN ({placeholders})",
        node_ids,
    )
    for target_id, weight in cursor.fetchall():
        weights[target_id] += weight

    conn.close()
    return weights


def _tier1_strip_bridges(nodes: List[SearchResult]) -> List[SearchResult]:
    """Tier 1: Remove all bridge nodes (1-hop external community nodes)."""
    return [n for n in nodes if n.salience_tier != "bridge"]


def _tier2_degrade_modes(nodes: List[SearchResult]) -> List[SearchResult]:
    """Tier 2: Degrade rendering modes progressively.

    full → signatures → map, applied to community nodes first,
    then anchor nodes if still over budget.
    """
    degraded = []
    for node in nodes:
        new_node = SearchResult(
            node_id=node.node_id,
            name=node.name,
            file_path=node.file_path,
            content=node.content,
            start_line=node.start_line,
            end_line=node.end_line,
            community_id=node.community_id,
            salience_tier=node.salience_tier,
            node_type=node.node_type,
            edge_weight_sum=node.edge_weight_sum,
            mode=node.mode,
        )
        if new_node.mode == "full":
            new_node.mode = "signatures"
        elif new_node.mode == "signatures":
            new_node.mode = "map"
        degraded.append(new_node)
    return degraded


def _tier3_drop_low_weight(nodes: List[SearchResult], db_path: str) -> List[SearchResult]:
    """Tier 3: Drop nodes with the lowest degree of connectivity.

    Computes incident edge weight sums and removes the bottom half.
    Always preserves at least anchor nodes.
    """
    if len(nodes) <= 1:
        return nodes

    node_ids = [n.node_id for n in nodes]
    weights = calculate_node_weights(node_ids, db_path)

    # Update edge_weight_sum on each result
    for node in nodes:
        node.edge_weight_sum = weights.get(node.node_id, 0.0)

    # Sort: anchors always first (preserved), then by weight descending
    anchors = [n for n in nodes if n.salience_tier == "anchor"]
    non_anchors = [n for n in nodes if n.salience_tier != "anchor"]
    non_anchors.sort(key=lambda n: n.edge_weight_sum, reverse=True)

    # Keep top half of non-anchors (at least 1)
    keep_count = max(1, len(non_anchors) // 2)
    return anchors + non_anchors[:keep_count]


def compress_to_budget(
    nodes: List[SearchResult],
    budget: int,
    db_path: str,
) -> List[SearchResult]:
    """Execute 3-tier progressive compression until output fits within budget.

    Returns the compressed node list. Each tier is applied only if the
    previous tier didn't bring the output under budget.
    """
    # Check if already under budget
    output = serialize_context(nodes)
    if len(output) <= budget:
        return nodes

    # Tier 1: Strip bridges
    nodes = _tier1_strip_bridges(nodes)
    output = serialize_context(nodes)
    if len(output) <= budget:
        return nodes

    # Tier 2: Degrade modes (may need multiple passes: full → sig → map)
    nodes = _tier2_degrade_modes(nodes)
    output = serialize_context(nodes)
    if len(output) <= budget:
        return nodes

    # Second degradation pass (signatures → map for remaining)
    nodes = _tier2_degrade_modes(nodes)
    output = serialize_context(nodes)
    if len(output) <= budget:
        return nodes

    # Tier 3: Drop low-weight nodes iteratively
    max_iterations = 5
    for _ in range(max_iterations):
        prev_count = len(nodes)
        nodes = _tier3_drop_low_weight(nodes, db_path)
        output = serialize_context(nodes)
        if len(output) <= budget or len(nodes) == prev_count:
            break

    return nodes
