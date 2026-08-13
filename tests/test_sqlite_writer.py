import sqlite3
from pathlib import Path

from buddhi.graph.model import CONTAINS, CodeGraph, GraphEdge, GraphNode
from buddhi.persist.sqlite_writer import write_sqlite


def _sample_graph() -> CodeGraph:
    graph = CodeGraph()
    graph.add_node(GraphNode(id="file:a.py", kind="file", name="a.py", qualified_name="a.py"))
    graph.add_node(
        GraphNode(
            id="class:a.py::Foo",
            kind="class",
            name="Foo",
            qualified_name="Foo",
            parent_id="file:a.py",
        )
    )
    graph.add_node(
        GraphNode(
            id="method:a.py::Foo.bar",
            kind="method",
            name="bar",
            qualified_name="Foo.bar",
            parent_id="class:a.py::Foo",
        )
    )
    graph.add_edge(GraphEdge(source="file:a.py", target="class:a.py::Foo", kind=CONTAINS))
    graph.add_edge(GraphEdge(source="class:a.py::Foo", target="method:a.py::Foo.bar", kind=CONTAINS))
    return graph


def test_write_sqlite_creates_expected_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))

    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"nodes", "edges", "meta"} <= tables

    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    assert node_count == 3


def test_descendant_recursive_cte(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))
    conn = sqlite3.connect(db_path)

    rows = conn.execute(
        """
        WITH RECURSIVE descendants(id) AS (
            SELECT id FROM nodes WHERE id = 'file:a.py'
            UNION ALL
            SELECT n.id FROM nodes n JOIN descendants d ON n.parent_id = d.id
        )
        SELECT id FROM nodes WHERE id IN descendants AND id != 'file:a.py'
        """
    ).fetchall()

    ids = {row[0] for row in rows}
    assert ids == {"class:a.py::Foo", "method:a.py::Foo.bar"}


def test_ancestor_recursive_cte(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))
    conn = sqlite3.connect(db_path)

    rows = conn.execute(
        """
        WITH RECURSIVE ancestors(id, parent_id, depth) AS (
            SELECT id, parent_id, 0 FROM nodes WHERE id = 'method:a.py::Foo.bar'
            UNION ALL
            SELECT n.id, n.parent_id, a.depth + 1
            FROM nodes n JOIN ancestors a ON n.id = a.parent_id
        )
        SELECT id FROM ancestors ORDER BY depth
        """
    ).fetchall()

    assert [row[0] for row in rows] == [
        "method:a.py::Foo.bar",
        "class:a.py::Foo",
        "file:a.py",
    ]


def test_rerun_overwrites_cleanly(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))

    conn = sqlite3.connect(db_path)
    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    assert node_count == 3
