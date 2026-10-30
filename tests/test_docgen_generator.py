from __future__ import annotations

import sqlite3
from pathlib import Path

from buddhi.docgen.generator import generate_docs_bundle
from buddhi.docgen.slug import SlugResolver, write_text_atomic_if_changed


def _create_test_sqlite_graph(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
    INSERT INTO meta VALUES ('schema_version', '2');
    INSERT INTO meta VALUES ('built_at_commit', 'abcdef123456');

    CREATE TABLE communities (
        id INTEGER PRIMARY KEY,
        label TEXT,
        node_count INTEGER,
        cohesion REAL,
        hub_node_id TEXT,
        top_files TEXT
    );
    INSERT INTO communities VALUES (0, 'Graph Core', 5, 0.85, 'node_hub', 'src/graph.py');
    INSERT INTO communities VALUES (1, 'Pipeline', 3, 0.70, 'node_pipe', 'src/pipe.py');

    CREATE TABLE nodes (
        id TEXT PRIMARY KEY,
        kind TEXT,
        name TEXT,
        qualified_name TEXT,
        file_path TEXT,
        language TEXT,
        start_line INTEGER,
        end_line INTEGER,
        parent_id TEXT,
        signature TEXT,
        external INTEGER DEFAULT 0,
        snippet TEXT,
        community_id INTEGER
    );
    INSERT INTO nodes VALUES ('node_hub', 'function', 'node_hub', 'graph.node_hub', 'src/graph.py', 'python', 1, 10, NULL, 'def node_hub()', 0, 'snippet1', 0);
    INSERT INTO nodes VALUES ('node_child', 'function', 'node_child', 'graph.node_child', 'src/graph.py', 'python', 12, 20, NULL, 'def node_child()', 0, 'snippet2', 0);
    INSERT INTO nodes VALUES ('node_pipe', 'function', 'node_pipe', 'pipe.node_pipe', 'src/pipe.py', 'python', 1, 15, NULL, 'def node_pipe()', 0, 'snippet3', 1);

    CREATE TABLE edges (
        source_id TEXT,
        target_id TEXT,
        kind TEXT,
        resolved INTEGER DEFAULT 1,
        confidence TEXT DEFAULT 'EXTRACTED',
        confidence_score REAL DEFAULT 1.0,
        context TEXT DEFAULT 'contains'
    );
    INSERT INTO edges VALUES ('node_child', 'node_hub', 'calls', 1, 'EXTRACTED', 1.0, 'call');
    INSERT INTO edges VALUES ('node_pipe', 'node_hub', 'calls', 1, 'INFERRED', 0.8, 'call');
    """)
    conn.commit()
    conn.close()


def test_generate_docs_bundle_creates_expected_artifacts(tmp_path: Path) -> None:
    graphs_dir = tmp_path / ".buddhi" / "graphs"
    graphs_dir.mkdir(parents=True)
    db_path = graphs_dir / "tree-graph.db"
    _create_test_sqlite_graph(db_path)

    count = generate_docs_bundle(tmp_path)
    assert count > 0

    docs_dir = tmp_path / ".buddhi" / "docs"
    assert (docs_dir / "index.md").is_file()
    assert (docs_dir / "architecture-report.md").is_file()

    # Community articles
    comm_dir = docs_dir / "communities"
    assert comm_dir.is_dir()
    comm_files = list(comm_dir.glob("*.md"))
    assert len(comm_files) == 2

    # Verify report content
    report_text = (docs_dir / "architecture-report.md").read_text(encoding="utf-8")
    assert "Architecture Report" in report_text
    assert "Graph Core" in report_text or "Pipeline" in report_text


def test_atomic_writes_and_zero_churn(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    written1 = write_text_atomic_if_changed(test_file, "content A")
    assert written1 is True
    assert test_file.read_text(encoding="utf-8") == "content A"

    # Second write with same content should return False and not touch mtime
    written2 = write_text_atomic_if_changed(test_file, "content A")
    assert written2 is False


def test_slug_resolver_collision_handling() -> None:
    resolver = SlugResolver()
    slug1 = resolver.register("Parser")
    slug2 = resolver.register("parser")
    slug3 = resolver.register("Parser")

    assert slug1 == "Parser"
    assert slug2 == "parser_2"
    assert slug3 == "Parser"  # same label reuses registered slug


def test_orphan_sweeping_removes_stale_articles(tmp_path: Path) -> None:
    graphs_dir = tmp_path / ".buddhi" / "graphs"
    graphs_dir.mkdir(parents=True)
    db_path = graphs_dir / "tree-graph.db"
    _create_test_sqlite_graph(db_path)

    docs_dir = tmp_path / ".buddhi" / "docs"
    comm_dir = docs_dir / "communities"
    comm_dir.mkdir(parents=True)
    stale_file = comm_dir / "stale_old_community.md"
    stale_file.write_text("old content", encoding="utf-8")

    generate_docs_bundle(tmp_path)
    assert not stale_file.exists()
