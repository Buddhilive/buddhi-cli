"""Leiden community detection over the symbol-level subgraph.

Ported from the earlier `graph/clustering.py` + `graph/weights.py` prototype, but
built in-memory from the current `CodeGraph` rather than re-reading a SQLite
database. Only class/function/method nodes participate (directory/file/external
nodes keep their kind-based coloring in the visualizer); only `calls`/`inherits`
edges between two such nodes count towards clustering — edges into synthetic
`external:` nodes are not real project relationships and would distort communities.
"""

from __future__ import annotations

from buddhi.graph.model import CALLS, CLASS, FUNCTION, INHERITS, METHOD, CodeGraph

_CLUSTERABLE_KINDS = (CLASS, FUNCTION, METHOD)
_EDGE_WEIGHTS = {CALLS: 3.0, INHERITS: 10.0}


def assign_communities(graph: CodeGraph) -> int:
    """Assign `community_id` to class/function/method nodes in place.

    Returns the number of distinct communities found, or 0 if clustering was
    skipped (igraph unavailable, or fewer than 2 clusterable nodes).
    """
    try:
        import igraph as ig  # type: ignore[import-untyped]
    except ImportError:
        return 0

    node_ids = [n.id for n in graph.nodes.values() if n.kind in _CLUSTERABLE_KINDS]
    if len(node_ids) < 2:
        return 0

    index = {node_id: i for i, node_id in enumerate(node_ids)}
    node_set = set(node_ids)

    edges: list[tuple[int, int]] = []
    weights: list[float] = []
    for edge in graph.edges:
        weight = _EDGE_WEIGHTS.get(edge.kind)
        if weight is None:
            continue
        if edge.source not in node_set or edge.target not in node_set:
            continue
        edges.append((index[edge.source], index[edge.target]))
        weights.append(weight)

    g = ig.Graph(n=len(node_ids), directed=True)
    if edges:
        g.add_edges(edges)
        g.es["weight"] = weights

    partition = g.community_leiden(
        objective_function="modularity",
        weights="weight" if edges else None,
    )

    for node_id, community_id in zip(node_ids, partition.membership, strict=True):
        graph.nodes[node_id].community_id = community_id

    return len(set(partition.membership))
