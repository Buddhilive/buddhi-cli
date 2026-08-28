from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import pytest

from buddhi.mcp.server import _get_db_path, buddhi_read, buddhi_search, mcp
from buddhi.persist.sqlite_writer import write_sqlite
from buddhi.graph.model import CodeGraph, GraphNode, FUNCTION, FILE


@pytest.fixture
def mock_db(tmp_path: Path) -> Path:
    buddhi_dir = tmp_path / ".buddhi" / "graphs"
    buddhi_dir.mkdir(parents=True, exist_ok=True)
    db_file = buddhi_dir / "tree-graph.db"

    graph = CodeGraph()
    graph.add_node(GraphNode(id="file:demo.py", kind=FILE, name="demo.py", qualified_name="demo.py", file_path="demo.py"))
    graph.add_node(
        GraphNode(
            id="function:demo.py::greet",
            kind=FUNCTION,
            name="greet",
            qualified_name="greet",
            file_path="demo.py",
            start_line=1,
            end_line=3,
            snippet="def greet(name: str):\n    return f'Hello, {name}'",
            signature="def greet(name: str):",
            community_id=1,
        )
    )
    write_sqlite(graph, db_file, root_path=str(tmp_path))
    return db_file


def test_mcp_server_registration():
    assert mcp.name == "buddhi-cli"


def test_mcp_path_resolution_override(tmp_path: Path):
    from buddhi.mcp import server

    explicit_path = tmp_path / "custom.db"
    server.OVERRIDE_DB_PATH = explicit_path
    try:
        assert _get_db_path() == explicit_path
    finally:
        server.OVERRIDE_DB_PATH = None


def test_mcp_path_resolution_upward(tmp_path: Path):
    buddhi_dir = tmp_path / ".buddhi" / "graphs"
    buddhi_dir.mkdir(parents=True, exist_ok=True)
    db_file = buddhi_dir / "tree-graph.db"
    db_file.write_text("test")

    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True, exist_ok=True)

    with patch("pathlib.Path.cwd", return_value=nested):
        resolved = _get_db_path()
        assert resolved.resolve() == db_file.resolve()


def test_mcp_search_execution(mock_db: Path):
    from buddhi.mcp import server

    server.OVERRIDE_DB_PATH = mock_db
    try:
        result = buddhi_search("greet")
        assert "greet" in result
        assert "--- START SYMBOL:" in result
    finally:
        server.OVERRIDE_DB_PATH = None


def test_mcp_read_execution(tmp_path: Path, mock_db: Path):
    from buddhi.mcp import server

    test_file = tmp_path / "demo.py"
    test_file.write_text("def greet(name: str):\n    return f'Hello, {name}'\n")

    server.OVERRIDE_DB_PATH = mock_db
    try:
        result = buddhi_read(filepath=str(test_file), mode="signatures")
        assert "def greet" in result
    finally:
        server.OVERRIDE_DB_PATH = None


def test_mcp_read_query_lookup(mock_db: Path):
    from buddhi.mcp import server

    server.OVERRIDE_DB_PATH = mock_db
    try:
        result = buddhi_read(query="demo.py")
        assert "demo.py" in result
    finally:
        server.OVERRIDE_DB_PATH = None
