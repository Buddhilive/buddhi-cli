import json
from pathlib import Path

from buddhi.graph.model import CONTAINS, CodeGraph, GraphEdge, GraphNode
from buddhi.persist.json_writer import to_cytoscape_elements, write_json


def _sample_graph() -> CodeGraph:
    graph = CodeGraph()
    graph.add_node(GraphNode(id="file:a.py", kind="file", name="a.py", qualified_name="a.py"))
    graph.add_node(
        GraphNode(
            id="function:a.py::f",
            kind="function",
            name="f",
            qualified_name="f",
            parent_id="file:a.py",
        )
    )
    graph.add_edge(GraphEdge(source="file:a.py", target="function:a.py::f", kind=CONTAINS))
    return graph


def test_cytoscape_shape_has_nodes_and_edges_with_data() -> None:
    elements = to_cytoscape_elements(_sample_graph())

    assert "nodes" in elements and "edges" in elements
    assert all("data" in n for n in elements["nodes"])
    assert all("data" in e for e in elements["edges"])

    node_data = {n["data"]["id"]: n["data"] for n in elements["nodes"]}
    assert node_data["function:a.py::f"]["parent"] == "file:a.py"


def test_write_json_is_valid_and_atomic(tmp_path: Path) -> None:
    json_path = tmp_path / "graph.json"
    write_json(_sample_graph(), json_path)

    assert json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(payload["nodes"]) == 2
    assert len(payload["edges"]) == 1
