import sqlite3
from pathlib import Path

from buddhi.graph.analyze import (
    find_import_cycles,
    find_shortest_path,
    get_god_nodes,
    get_surprising_connections,
)
from buddhi.graph.blast_radius import compute_blast_radius
from buddhi.graph.model import (
    CALLS,
    IMPORTS,
    CodeGraph,
    CommunityInfo,
    GraphEdge,
    GraphNode,
)
from buddhi.persist.sqlite_writer import write_sqlite


def _create_test_db(tmp_path: Path) -> Path:
    graph = CodeGraph()
    # Nodes
    graph.add_node(
        GraphNode(
            id="file:a.py",
            kind="file",
            name="a.py",
            qualified_name="a.py",
            file_path="a.py",
        )
    )
    graph.add_node(
        GraphNode(
            id="file:b.py",
            kind="file",
            name="b.py",
            qualified_name="b.py",
            file_path="b.py",
        )
    )
    graph.add_node(
        GraphNode(
            id="function:a.py::caller",
            kind="function",
            name="caller",
            qualified_name="caller",
            file_path="a.py",
            community_id=1,
        )
    )
    graph.add_node(
        GraphNode(
            id="function:b.py::target",
            kind="function",
            name="target",
            qualified_name="target",
            file_path="b.py",
            community_id=2,
        )
    )
    graph.add_node(
        GraphNode(
            id="function:b.py::god_hub",
            kind="function",
            name="god_hub",
            qualified_name="god_hub",
            file_path="b.py",
            community_id=2,
        )
    )

    # Edges
    graph.add_edge(GraphEdge(source="file:a.py", target="file:b.py", kind=IMPORTS))
    graph.add_edge(
        GraphEdge(
            source="function:a.py::caller",
            target="function:b.py::target",
            kind=CALLS,
            confidence="EXTRACTED",
        )
    )
    graph.add_edge(
        GraphEdge(
            source="function:a.py::caller",
            target="function:b.py::god_hub",
            kind=CALLS,
            confidence="INFERRED",
        )
    )
    graph.add_edge(
        GraphEdge(
            source="function:b.py::target",
            target="function:b.py::god_hub",
            kind=CALLS,
            confidence="EXTRACTED",
        )
    )

    graph.communities[1] = CommunityInfo(
        id=1, label="a_comm", node_count=1, cohesion=1.0
    )
    graph.communities[2] = CommunityInfo(
        id=2, label="b_comm", node_count=2, cohesion=0.8
    )
    graph.built_at_commit = "abcd" * 10

    db_path = tmp_path / "tree-graph.db"
    write_sqlite(graph, db_path, root_path=str(tmp_path))
    return db_path


def test_god_nodes_and_surprises(tmp_path: Path) -> None:
    db_path = _create_test_db(tmp_path)
    conn = sqlite3.connect(db_path)

    gods = get_god_nodes(conn, top_n=5)
    assert len(gods) >= 1
    names = {g["name"] for g in gods}
    assert "god_hub" in names and "caller" in names

    surprises = get_surprising_connections(conn, top_n=5)
    assert len(surprises) >= 1
    assert any(
        s["source_name"] == "caller" and s["target_name"] == "god_hub"
        for s in surprises
    )
    conn.close()


def test_shortest_path_and_cycles(tmp_path: Path) -> None:
    db_path = _create_test_db(tmp_path)
    conn = sqlite3.connect(db_path)

    path_res = find_shortest_path(conn, "caller", "god_hub")
    assert path_res["found"] is True
    assert path_res["hops"] == 1

    cycles = find_import_cycles(conn)
    assert cycles == []
    conn.close()


def test_blast_radius(tmp_path: Path) -> None:
    db_path = _create_test_db(tmp_path)
    conn = sqlite3.connect(db_path)

    report = compute_blast_radius(
        conn, targets=["b.py"], max_hops=2, root_path=tmp_path
    )
    assert "b.py" in report.target_files
    assert "function:a.py::caller" in report.direct_callers
    assert len(report.affected_communities) >= 1
    conn.close()
