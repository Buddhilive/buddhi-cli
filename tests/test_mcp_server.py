"""Tests for the Buddhi MCP server."""
import sqlite3
from pathlib import Path
import pytest
from unittest.mock import patch

from buddhi_ai.mcp.server import (
    _get_db_path,
    buddhi_search,
    mcp,
)


@pytest.fixture
def mock_db_path(tmp_path: Path) -> Path:
    """Create a temporary mock buddhi graph database."""
    buddhi_dir = tmp_path / ".buddhi"
    buddhi_dir.mkdir(parents=True, exist_ok=True)
    db_file = buddhi_dir / "graph.db"
    
    # Initialize schema
    conn = sqlite3.connect(db_file)
    schema_path = Path(__file__).parent.parent / "src" / "buddhi_ai" / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        
    # Insert a sample file & node
    conn.execute("INSERT INTO files (id, path, mtime, last_scanned) VALUES (1, 'src/test.py', 1.0, 1.0)")
    conn.execute(
        "INSERT INTO nodes (id, file_id, language, node_type, name, content, start_line, end_line, community_id) "
        "VALUES (1, 1, 'python', 'function_definition', 'hello_world', "
        "'def hello_world():\\n    print(\"Hello\")', 1, 3, 0)"
    )
    conn.commit()
    conn.close()
    return db_file


class TestMCPPathResolution:
    def test_override_db_path(self):
        """Verify that when OVERRIDE_DB_PATH is set, it is returned directly."""
        from buddhi_ai.mcp import server
        expected = Path("/some/explicit/path/graph.db")
        server.OVERRIDE_DB_PATH = expected
        try:
            assert _get_db_path() == expected
        finally:
            server.OVERRIDE_DB_PATH = None

    def test_cwd_recursive_upward_detection(self, tmp_path: Path):
        """Verify that DB is discovered by walking up parent directories."""
        buddhi_dir = tmp_path / ".buddhi"
        buddhi_dir.mkdir(parents=True, exist_ok=True)
        db_file = buddhi_dir / "graph.db"
        db_file.write_text("dummy db content")

        # Nested folder inside workspace
        nested_dir = tmp_path / "src" / "components" / "auth"
        nested_dir.mkdir(parents=True, exist_ok=True)

        with patch("pathlib.Path.cwd", return_value=nested_dir):
            resolved = _get_db_path()
            assert resolved.resolve() == db_file.resolve()

    def test_fallback_cwd_resolution(self, tmp_path: Path):
        """Verify fallback to CWD/.buddhi/graph.db if not found in parents."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            resolved = _get_db_path()
            expected = tmp_path / ".buddhi" / "graph.db"
            assert resolved.resolve() == expected.resolve()


class TestMCPToolExecution:
    def test_missing_database_error(self, tmp_path: Path):
        """Verify tool returns a clean error message if DB is missing."""
        from buddhi_ai.mcp import server
        server.OVERRIDE_DB_PATH = tmp_path / "nonexistent" / "graph.db"
        try:
            result = buddhi_search("test")
            assert "Error: Buddhi database not found" in result
            assert "buddhi init" in result
        finally:
            server.OVERRIDE_DB_PATH = None

    def test_successful_search(self, mock_db_path: Path):
        """Verify successful search tool invocation returns serialized context."""
        from buddhi_ai.mcp import server
        server.OVERRIDE_DB_PATH = mock_db_path
        try:
            result = buddhi_search("hello_world")
            assert "hello_world" in result
            assert "--- START SYMBOL:" in result
            assert "src/test.py" in result
        finally:
            server.OVERRIDE_DB_PATH = None

    def test_exception_handling(self, mock_db_path: Path):
        """Verify search failures/exceptions are gracefully caught and reported."""
        from buddhi_ai.mcp import server
        server.OVERRIDE_DB_PATH = mock_db_path
        
        # Patch buddhi_search to raise an error
        with patch("buddhi_ai.search.search.buddhi_search", side_effect=ValueError("Db corrupt")):
            result = buddhi_search("hello")
            assert "Error executing search: Db corrupt" in result
            
        server.OVERRIDE_DB_PATH = None


class TestFastMCPMetadata:
    def test_server_registrations(self):
        """Verify the server registration metadata."""
        assert mcp.name == "buddhi-cli"
        
        # Verify tool is registered
        registered_tools = mcp._tool_manager.list_tools()
        buddhi_tool = next((t for t in registered_tools if t.name == "buddhi_search"), None)
        
        assert buddhi_tool is not None
        assert buddhi_tool.name == "buddhi_search"
        assert "Search the codebase using Buddhi's topology-driven" in buddhi_tool.description
