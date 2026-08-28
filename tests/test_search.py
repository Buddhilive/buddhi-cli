from __future__ import annotations

from pathlib import Path
import sqlite3
from buddhi.mcp.tools.search import (
    SearchResult,
    _tier1_strip_bridges,
    _tier2_degrade_modes,
    expand_query,
    execute_buddhi_search,
    filter_low_entropy_lines,
    serialize_context,
    u_curve_sort,
)
from buddhi.persist.sqlite_writer import write_sqlite
from buddhi.graph.model import (
    CodeGraph,
    GraphEdge,
    GraphNode,
    CALLS,
    CONTAINS,
    FUNCTION,
    FILE,
)


def test_expand_query():
    assert expand_query("getUserData") == ["get", "User", "Data"]
    assert expand_query("parse_file") == ["parse", "file"]
    assert expand_query("XMLParser") == ["XML", "Parser"]
    assert expand_query("a_b") == []


def test_entropy_filtering():
    code = "def parse(x):\n/////////////////////////////////////////\n    return x"
    filtered = filter_low_entropy_lines(code)
    assert "def parse" in filtered
    assert "return x" in filtered
    assert "/////////////////////////////////////////" not in filtered


def test_u_curve_sort():
    r1 = SearchResult(
        node_id="1",
        name="fn_anchor",
        file_path="a.py",
        content="def fn_anchor(): pass",
        signature="def fn_anchor(): pass",
        start_line=1,
        end_line=2,
        community_id=1,
        salience_tier="anchor",
        node_type="function",
    )
    r2 = SearchResult(
        node_id="2",
        name="fn_comm",
        file_path="a.py",
        content="def fn_comm(): pass",
        signature="def fn_comm(): pass",
        start_line=3,
        end_line=4,
        community_id=1,
        salience_tier="community",
        node_type="function",
    )
    r3 = SearchResult(
        node_id="3",
        name="fn_bridge",
        file_path="b.py",
        content="def fn_bridge(): pass",
        signature="def fn_bridge(): pass",
        start_line=1,
        end_line=2,
        community_id=2,
        salience_tier="bridge",
        node_type="function",
    )

    sorted_nodes = u_curve_sort([r2, r3, r1])
    assert sorted_nodes[0].name == "fn_anchor"
    assert sorted_nodes[1].name == "fn_bridge"
    assert sorted_nodes[2].name == "fn_comm"


def test_search_execution_with_graph(tmp_path: Path):
    graph = CodeGraph()
    n_file = GraphNode(id="file:a.py", kind=FILE, name="a.py", qualified_name="a.py", file_path="a.py")
    n_fn1 = GraphNode(
        id="function:a.py::parse_input",
        kind=FUNCTION,
        name="parse_input",
        qualified_name="parse_input",
        file_path="a.py",
        start_line=1,
        end_line=5,
        snippet="def parse_input(data):\n    return data.strip()",
        signature="def parse_input(data):",
        community_id=1,
    )
    n_fn2 = GraphNode(
        id="function:a.py::helper_func",
        kind=FUNCTION,
        name="helper_func",
        qualified_name="helper_func",
        file_path="a.py",
        start_line=7,
        end_line=10,
        snippet="def helper_func():\n    return 42",
        signature="def helper_func():",
        community_id=1,
    )
    graph.add_node(n_file)
    graph.add_node(n_fn1)
    graph.add_node(n_fn2)
    graph.add_edge(GraphEdge(source="file:a.py", target="function:a.py::parse_input", kind=CONTAINS))
    graph.add_edge(GraphEdge(source="file:a.py", target="function:a.py::helper_func", kind=CONTAINS))
    graph.add_edge(GraphEdge(source="function:a.py::parse_input", target="function:a.py::helper_func", kind=CALLS))

    db_path = tmp_path / "tree-graph.db"
    write_sqlite(graph, db_path, root_path=str(tmp_path))

    # Basic search
    result = execute_buddhi_search("parse_input", str(db_path))
    assert "parse_input" in result
    assert "helper_func" in result  # Community co-member
    assert "--- START SYMBOL:" in result

    # Mode signatures
    sig_result = execute_buddhi_search("parse_input", str(db_path), mode="signatures")
    assert "def parse_input(data):" in sig_result

    # Mode map
    map_result = execute_buddhi_search("parse_input", str(db_path), mode="map")
    assert "parse_input (function) — a.py:L1-L5" in map_result


def test_search_fallback(tmp_path: Path):
    db_path = tmp_path / "empty-graph.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT, file_path TEXT, language TEXT, start_line INTEGER, end_line INTEGER, parent_id TEXT, signature TEXT, external INTEGER, snippet TEXT, community_id INTEGER)"
    )
    conn.execute(
        "INSERT INTO nodes VALUES ('fn:x', 'function', 'compute_total', 'compute_total', 'x.py', 'python', 1, 5, NULL, 'def compute_total():', 0, 'some snippet', 0)"
    )
    conn.commit()
    conn.close()

    # Search for something in snippet or name
    result = execute_buddhi_search("compute_total", str(db_path))
    assert "compute_total" in result
