from buddhi.graph.clustering import assign_communities
from buddhi.graph.model import CALLS, CodeGraph, GraphEdge, GraphNode


def _method(node_id: str) -> GraphNode:
    return GraphNode(id=node_id, kind="method", name=node_id, qualified_name=node_id)


def test_two_disconnected_clusters_get_distinct_communities() -> None:
    graph = CodeGraph()
    for node_id in ("a1", "a2", "b1", "b2"):
        graph.add_node(_method(node_id))
    graph.add_edge(GraphEdge(source="a1", target="a2", kind=CALLS))
    graph.add_edge(GraphEdge(source="b1", target="b2", kind=CALLS))

    count = assign_communities(graph)

    assert count >= 2
    assert graph.nodes["a1"].community_id == graph.nodes["a2"].community_id
    assert graph.nodes["b1"].community_id == graph.nodes["b2"].community_id
    assert graph.nodes["a1"].community_id != graph.nodes["b1"].community_id


def test_non_clusterable_kinds_stay_none() -> None:
    graph = CodeGraph()
    graph.add_node(GraphNode(id="dir:x", kind="directory", name="x", qualified_name="x"))
    graph.add_node(GraphNode(id="file:x.py", kind="file", name="x.py", qualified_name="x.py"))
    graph.add_node(GraphNode(id="external:os", kind="external", name="os", qualified_name="os", external=True))
    graph.add_node(_method("m1"))
    graph.add_node(_method("m2"))
    graph.add_edge(GraphEdge(source="m1", target="m2", kind=CALLS))
    graph.add_edge(GraphEdge(source="m1", target="external:os", kind=CALLS))

    assign_communities(graph)

    assert graph.nodes["dir:x"].community_id is None
    assert graph.nodes["file:x.py"].community_id is None
    assert graph.nodes["external:os"].community_id is None


def test_empty_or_tiny_graph_is_skipped_without_crashing() -> None:
    graph = CodeGraph()
    assert assign_communities(graph) == 0

    graph.add_node(_method("solo"))
    assert assign_communities(graph) == 0
    assert graph.nodes["solo"].community_id is None
