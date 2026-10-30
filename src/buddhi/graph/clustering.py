"""Leiden community detection with deterministic sorting, super-hub exclusion, and cohesion metrics.

Only class/function/method nodes participate; only `calls`/`inherits` edges
between clusterable project nodes count. Produces CommunityInfo records with
hub-derived names and cohesion scores.
"""

from __future__ import annotations

import collections
import random
from pathlib import PurePosixPath

from buddhi.graph.model import (
    CALLS,
    CLASS,
    FUNCTION,
    INHERITS,
    METHOD,
    CodeGraph,
    CommunityInfo,
)

_CLUSTERABLE_KINDS = (CLASS, FUNCTION, METHOD)
_EDGE_WEIGHTS = {CALLS: 3.0, INHERITS: 10.0}


def _calc_cohesion(nodes: list[str], internal_edge_count: int) -> float:
    n = len(nodes)
    if n <= 1:
        return 1.0
    max_possible = n * (n - 1)
    if max_possible == 0:
        return 1.0
    return min(1.0, internal_edge_count / max_possible)


def assign_communities(graph: CodeGraph) -> int:
    """Assign deterministic community_id and CommunityInfo records to CodeGraph.

    Returns distinct community count (or 0 if skipped).
    """
    try:
        import igraph as ig  # type: ignore[import-untyped]
    except ImportError:
        return 0

    # 1. Deterministic canonical node ordering
    node_ids = sorted(
        [n.id for n in graph.nodes.values() if n.kind in _CLUSTERABLE_KINDS]
    )
    if len(node_ids) < 2:
        return 0

    node_set = set(node_ids)
    node_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    # Count node incident degrees to detect super-hubs
    degree_counts: dict[str, int] = collections.defaultdict(int)
    for edge in graph.edges:
        if (
            edge.kind in _EDGE_WEIGHTS
            and edge.source in node_set
            and edge.target in node_set
        ):
            degree_counts[edge.source] += 1
            degree_counts[edge.target] += 1

    degrees = sorted(degree_counts.values())
    p99_idx = int(0.99 * len(degrees)) if degrees else 0
    p99_deg = degrees[p99_idx] if degrees else 50
    hub_threshold = max(50, p99_deg)

    super_hubs = {nid for nid, deg in degree_counts.items() if deg > hub_threshold}

    # 2. Canonical edge sorting (sorted by source index, target index, kind)
    sorted_raw_edges = sorted(
        [
            (node_to_idx[e.source], node_to_idx[e.target], e.kind, e.source, e.target)
            for e in graph.edges
            if e.kind in _EDGE_WEIGHTS and e.source in node_set and e.target in node_set
        ],
        key=lambda x: (x[0], x[1], x[2]),
    )

    # Filter out super-hubs from initial partitioning
    partition_nodes = [nid for nid in node_ids if nid not in super_hubs]
    part_to_idx = {nid: i for i, nid in enumerate(partition_nodes)}
    part_set = set(partition_nodes)

    part_edges: list[tuple[int, int]] = []
    part_weights: list[float] = []

    for src_idx, tgt_idx, kind, src_id, tgt_id in sorted_raw_edges:
        if src_id in part_set and tgt_id in part_set:
            part_edges.append((part_to_idx[src_id], part_to_idx[tgt_id]))
            part_weights.append(_EDGE_WEIGHTS[kind])

    membership_map: dict[str, int] = {}

    if len(partition_nodes) >= 2 and part_edges:
        g = ig.Graph(n=len(partition_nodes), directed=True)
        g.add_edges(part_edges)
        g.es["weight"] = part_weights

        ig.set_random_number_generator(random.Random(42))
        partition = g.community_leiden(
            objective_function="modularity",
            weights="weight",
        )
        for nid, comm_id in zip(partition_nodes, partition.membership, strict=True):
            membership_map[nid] = comm_id
    else:
        for idx, nid in enumerate(partition_nodes):
            membership_map[nid] = idx

    # 3. Reattach super-hubs by majority-neighbor community
    hub_adj: dict[str, collections.Counter[int]] = collections.defaultdict(
        collections.Counter
    )
    for src_idx, tgt_idx, kind, src_id, tgt_id in sorted_raw_edges:
        if src_id in super_hubs and tgt_id in membership_map:
            hub_adj[src_id][membership_map[tgt_id]] += 1
        elif tgt_id in super_hubs and src_id in membership_map:
            hub_adj[tgt_id][membership_map[src_id]] += 1

    max_comm_id = max(membership_map.values(), default=0)
    for hub_id in sorted(super_hubs):
        counter = hub_adj.get(hub_id)
        if counter:
            best_comm = min(counter.items(), key=lambda x: (-x[1], x[0]))[0]
            membership_map[hub_id] = best_comm
        else:
            max_comm_id += 1
            membership_map[hub_id] = max_comm_id

    # 4. Normalize community IDs to consecutive ints 1..K (1-indexed)
    comm_groups: dict[int, list[str]] = collections.defaultdict(list)
    for nid in node_ids:
        raw_id = membership_map.get(nid, 0)
        comm_groups[raw_id].append(nid)

    # Sort communities deterministically by group size descending, then first node id
    sorted_comm_keys = sorted(
        comm_groups.keys(),
        key=lambda k: (
            -len(comm_groups[k]),
            min(comm_groups[k]) if comm_groups[k] else "",
        ),
    )

    id_remap = {old_k: new_k for new_k, old_k in enumerate(sorted_comm_keys, start=1)}

    for nid in node_ids:
        graph.nodes[nid].community_id = id_remap[membership_map[nid]]

    # 5. Compute internal edge counts and CommunityInfo
    comm_internal_edges: dict[int, int] = collections.defaultdict(int)
    for src_idx, tgt_idx, kind, src_id, tgt_id in sorted_raw_edges:
        c1 = graph.nodes[src_id].community_id
        c2 = graph.nodes[tgt_id].community_id
        if c1 is not None and c1 == c2:
            comm_internal_edges[c1] += 1

    graph.communities.clear()
    for new_id, old_key in enumerate(sorted_comm_keys, start=1):
        members = comm_groups[old_key]
        n_count = len(members)

        # Pick highest-degree symbol in community as hub
        member_degrees = [(degree_counts.get(m, 0), m) for m in members]
        member_degrees.sort(key=lambda x: (-x[0], x[1]))
        hub_node_id = member_degrees[0][1] if member_degrees else None
        hub_node = graph.nodes.get(hub_node_id) if hub_node_id else None

        if hub_node and hub_node.file_path:
            parent_dir = PurePosixPath(hub_node.file_path).parent.name or "root"
            label = f"{parent_dir}/{hub_node.name}"
        elif hub_node:
            label = hub_node.name
        else:
            label = f"Community_{new_id}"

        # Top files
        file_counts = collections.Counter(
            graph.nodes[m].file_path for m in members if graph.nodes[m].file_path
        )
        top_files = [fp for fp, _ in file_counts.most_common(5) if fp]

        cohesion = _calc_cohesion(members, comm_internal_edges.get(new_id, 0))

        graph.communities[new_id] = CommunityInfo(
            id=new_id,
            label=label,
            node_count=n_count,
            cohesion=round(cohesion, 4),
            hub_node_id=hub_node_id,
            top_files=top_files,
        )

    return len(graph.communities)
