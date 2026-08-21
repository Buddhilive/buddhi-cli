from pathlib import Path

from buddhi.graph.model import CodeGraph, GraphNode
from buddhi.persist.html_writer import VIS_NETWORK_CDN_URL, write_html


def test_write_html_embeds_cdn_and_graph_data(tmp_path: Path) -> None:
    graph = CodeGraph()
    graph.add_node(GraphNode(id="file:a.py", kind="file", name="a.py", qualified_name="a.py"))

    html_path = tmp_path / "graph.html"
    write_html(graph, html_path, root_label="a.py")

    content = html_path.read_text(encoding="utf-8")
    assert VIS_NETWORK_CDN_URL in content
    assert "graphData" in content
    assert '"id":"file:a.py"' in content
