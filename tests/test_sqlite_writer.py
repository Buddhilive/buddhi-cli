import sqlite3
from pathlib import Path

from buddhi.graph.model import (
    CONFIDENCE_EXTRACTED,
    CONTAINS,
    CONTEXT_CONTAINS,
    CodeGraph,
    CommunityInfo,
    GraphEdge,
    GraphNode,
)
from buddhi.persist.sqlite_writer import (
    get_db_capabilities,
    load_extract_cache,
    write_sqlite,
)


def _sample_graph() -> CodeGraph:
    graph = CodeGraph()
    graph.add_node(
        GraphNode(id="file:a.py", kind="file", name="a.py", qualified_name="a.py")
    )
    graph.add_node(
        GraphNode(
            id="class:a.py::Foo",
            kind="class",
            name="Foo",
            qualified_name="Foo",
            parent_id="file:a.py",
            community_id=1,
        )
    )
    graph.add_node(
        GraphNode(
            id="method:a.py::Foo.bar",
            kind="method",
            name="bar",
            qualified_name="Foo.bar",
            parent_id="class:a.py::Foo",
            community_id=1,
        )
    )
    graph.add_edge(
        GraphEdge(source="file:a.py", target="class:a.py::Foo", kind=CONTAINS)
    )
    graph.add_edge(
        GraphEdge(
            source="class:a.py::Foo", target="method:a.py::Foo.bar", kind=CONTAINS
        )
    )
    graph.communities[1] = CommunityInfo(
        id=1,
        label="FooHub",
        node_count=2,
        cohesion=0.85,
        hub_node_id="class:a.py::Foo",
        top_files=["a.py"],
    )
    graph.built_at_commit = "0123456789abcdef0123456789abcdef01234567"
    return graph


def test_write_sqlite_creates_expected_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    cache_entries = [
        ("a.py", "hash123", "python", '{"defs":[]}', "2026-10-27T00:00:00Z")
    ]
    write_sqlite(
        _sample_graph(),
        db_path,
        root_path=str(tmp_path),
        extract_cache_entries=cache_entries,
    )

    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"nodes", "edges", "communities", "extract_cache", "meta"} <= tables

    caps = get_db_capabilities(conn)
    assert caps["has_communities"] is True
    assert caps["has_extract_cache"] is True
    assert caps["has_edge_confidence"] is True
    assert caps["has_edge_context"] is True

    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    assert node_count == 3

    edge_row = conn.execute(
        "SELECT confidence, confidence_score, context FROM edges LIMIT 1"
    ).fetchone()
    assert edge_row == (CONFIDENCE_EXTRACTED, 1.0, CONTEXT_CONTAINS)

    comm_row = conn.execute(
        "SELECT id, label, node_count, cohesion, hub_node_id FROM communities WHERE id = 1"
    ).fetchone()
    assert comm_row == (1, "FooHub", 2, 0.85, "class:a.py::Foo")

    meta_dict = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    assert meta_dict["schema_version"] == "2"
    assert meta_dict["built_at_commit"] == "0123456789abcdef0123456789abcdef01234567"
    conn.close()

    loaded_cache = load_extract_cache(db_path)
    assert "a.py" in loaded_cache
    assert loaded_cache["a.py"][0] == "hash123"
    assert loaded_cache["a.py"][1] == "python"


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
    conn.close()


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
    conn.close()


def test_rerun_overwrites_cleanly(tmp_path: Path) -> None:
    db_path = tmp_path / "graph.db"
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))
    write_sqlite(_sample_graph(), db_path, root_path=str(tmp_path))

    conn = sqlite3.connect(db_path)
    node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    assert node_count == 3
    conn.close()
