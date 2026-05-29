"""Tests for the buddhi_search pipeline."""
import sqlite3
from pathlib import Path

import pytest

from buddhi_ai.search.query_expansion import expand_query, build_fts_query
from buddhi_ai.search.formatter import (
    SearchResult,
    extract_signature,
    extract_map_entry,
    filter_low_entropy_lines,
    u_curve_sort,
    serialize_context,
    render_content,
)
from buddhi_ai.search.compressor import (
    _tier1_strip_bridges,
    _tier2_degrade_modes,
)
from buddhi_ai.search.search import buddhi_search


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Create a test SQLite database with schema, FTS5, and sample data."""
    db_file = str(tmp_path / "graph.db")
    conn = sqlite3.connect(db_file)

    # Run schema
    schema_path = Path(__file__).parent.parent / "src" / "buddhi_ai" / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # Insert files
    conn.execute("INSERT INTO files (id, path, mtime, last_scanned) VALUES (1, 'src/parser.py', 1.0, 1.0)")
    conn.execute("INSERT INTO files (id, path, mtime, last_scanned) VALUES (2, 'src/utils.py', 1.0, 1.0)")
    conn.execute("INSERT INTO files (id, path, mtime, last_scanned) VALUES (3, 'src/db.py', 1.0, 1.0)")

    # Insert nodes in community 0 (parser domain)
    conn.execute(
        "INSERT INTO nodes (id, file_id, language, node_type, name, content, start_line, end_line, community_id) "
        "VALUES (1, 1, 'python', 'function_definition', 'parse_file', "
        "'def parse_file(filepath: Path) -> List[Dict]:\\n    \"\"\"Parse a file.\"\"\"\\n    pass', 10, 20, 0)"
    )
    conn.execute(
        "INSERT INTO nodes (id, file_id, language, node_type, name, content, start_line, end_line, community_id) "
        "VALUES (2, 1, 'python', 'function_definition', 'walk_tree', "
        "'def walk_tree(node, source):\\n    pass', 25, 40, 0)"
    )

    # Insert node in community 1 (utils domain)
    conn.execute(
        "INSERT INTO nodes (id, file_id, language, node_type, name, content, start_line, end_line, community_id) "
        "VALUES (3, 2, 'python', 'function_definition', 'helper_util', "
        "'def helper_util(x):\\n    return x * 2', 1, 5, 1)"
    )

    # Insert node in community 2 (db domain)
    conn.execute(
        "INSERT INTO nodes (id, file_id, language, node_type, name, content, start_line, end_line, community_id) "
        "VALUES (4, 3, 'python', 'class_definition', 'DatabaseConnection', "
        "'class DatabaseConnection:\\n    \"\"\"DB conn.\"\"\"\\n    def connect(self):\\n        pass', 1, 15, 2)"
    )

    # Insert edges
    # parse_file -> walk_tree (internal call, same community)
    conn.execute("INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (1, 2, 'call', 3.0)")
    # parse_file -> helper_util (cross-community bridge, call weight)
    conn.execute("INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (1, 3, 'call', 3.0)")
    # walk_tree -> DatabaseConnection (cross-community bridge, weak reference)
    conn.execute("INSERT INTO edges (source_id, target_id, relationship_type, weight) VALUES (2, 4, 'reference', 1.0)")

    conn.commit()
    conn.close()
    return db_file


# --------------------------------------------------------------------------
# Query Expansion Tests
# --------------------------------------------------------------------------

class TestQueryExpansion:
    def test_camel_case(self):
        assert expand_query("getUserData") == ["get", "User", "Data"]

    def test_pascal_case(self):
        assert expand_query("UserService") == ["User", "Service"]

    def test_snake_case(self):
        assert expand_query("parse_file") == ["parse", "file"]

    def test_mixed_case_with_acronym(self):
        result = expand_query("XMLParser")
        assert result == ["XML", "Parser"]

    def test_short_tokens_filtered(self):
        result = expand_query("a_b_cd")
        assert result == ["cd"]

    def test_space_separated(self):
        result = expand_query("load graph builder")
        assert result == ["load", "graph", "builder"]

    def test_empty_string(self):
        assert expand_query("") == []

    def test_build_fts_single(self):
        assert build_fts_query(["parse"]) == "parse"

    def test_build_fts_multiple(self):
        assert build_fts_query(["get", "User", "Data"]) == "get OR User OR Data"

    def test_build_fts_empty(self):
        assert build_fts_query([]) == ""


# --------------------------------------------------------------------------
# Formatter Tests
# --------------------------------------------------------------------------

class TestFormatter:
    def _make_result(self, tier: str = "anchor", mode: str = "full", **kwargs) -> SearchResult:
        defaults = dict(
            node_id=1,
            name="test_func",
            file_path="src/test.py",
            content="def test_func(x: int) -> int:\n    return x + 1",
            start_line=10,
            end_line=12,
            community_id=0,
            salience_tier=tier,
            node_type="function_definition",
        )
        defaults.update(kwargs)
        r = SearchResult(**defaults)
        r.mode = mode
        return r

    def test_extract_signature_function(self):
        content = "def parse_file(filepath: Path) -> List[Dict]:\n    \"\"\"Parse a file.\"\"\"\n    pass\n    return result"
        sig = extract_signature(content, "function_definition")
        assert "def parse_file" in sig
        assert "return result" not in sig

    def test_extract_signature_class(self):
        content = "class MyClass:\n    \"\"\"A class.\"\"\"\n    def method(self):\n        pass"
        sig = extract_signature(content, "class_definition")
        assert "class MyClass" in sig
        assert "def method" not in sig

    def test_extract_map_entry(self):
        result = self._make_result()
        entry = extract_map_entry(result)
        assert "test_func" in entry
        assert "src/test.py" in entry
        assert "L10" in entry

    def test_u_curve_sort_ordering(self):
        anchor = self._make_result(tier="anchor", name="anchor_fn")
        community = self._make_result(tier="community", name="comm_fn")
        bridge = self._make_result(tier="bridge", name="bridge_fn")

        sorted_nodes = u_curve_sort([community, bridge, anchor])

        assert sorted_nodes[0].name == "anchor_fn"     # Top
        assert sorted_nodes[1].name == "bridge_fn"      # Middle (dead zone)
        assert sorted_nodes[2].name == "comm_fn"         # Bottom

    def test_serialize_context_delimiters(self):
        result = self._make_result()
        output = serialize_context([result])
        assert "--- START SYMBOL:" in output
        assert "--- END SYMBOL ---" in output
        assert "src/test.py::test_func" in output

    def test_render_content_full_mode(self):
        result = self._make_result(mode="full")
        content = render_content(result)
        assert "def test_func" in content
        assert "return x + 1" in content

    def test_render_content_signatures_mode(self):
        result = self._make_result(mode="signatures")
        content = render_content(result)
        assert "def test_func" in content

    def test_render_content_map_mode(self):
        result = self._make_result(mode="map")
        content = render_content(result)
        assert "test_func" in content
        assert "function_definition" in content
        assert "L10" in content

    def test_filter_low_entropy_keeps_code(self):
        code = "def complex_function(x: int, y: float) -> Dict[str, Any]:"
        result = filter_low_entropy_lines(code)
        assert "def complex_function" in result

    def test_filter_low_entropy_drops_boilerplate(self):
        boilerplate = "//////////////////////////////////////////////////////"
        code = "def real_code(x):\n" + boilerplate + "\n    return x"
        result = filter_low_entropy_lines(code)
        assert boilerplate not in result
        assert "def real_code" in result


# --------------------------------------------------------------------------
# Compressor Tests
# --------------------------------------------------------------------------

class TestCompressor:
    def _make_result(self, tier: str, name: str, mode: str = "full") -> SearchResult:
        r = SearchResult(
            node_id=hash(name) % 10000,
            name=name,
            file_path="src/test.py",
            content="def " + name + "(x):\n    return x * 2\n    # some more code\n    pass",
            start_line=1,
            end_line=4,
            community_id=0,
            salience_tier=tier,
            node_type="function_definition",
        )
        r.mode = mode
        return r

    def test_tier1_removes_bridges(self):
        nodes = [
            self._make_result("anchor", "anchor_fn"),
            self._make_result("community", "comm_fn"),
            self._make_result("bridge", "bridge_fn"),
        ]
        result = _tier1_strip_bridges(nodes)
        tiers = [n.salience_tier for n in result]
        assert "bridge" not in tiers
        assert len(result) == 2

    def test_tier2_degrades_modes(self):
        nodes = [
            self._make_result("anchor", "fn1", mode="full"),
            self._make_result("community", "fn2", mode="full"),
        ]
        result = _tier2_degrade_modes(nodes)
        assert all(n.mode == "signatures" for n in result)

        result2 = _tier2_degrade_modes(result)
        assert all(n.mode == "map" for n in result2)


# --------------------------------------------------------------------------
# Integration Tests (End-to-End)
# --------------------------------------------------------------------------

class TestBuddhiSearch:
    def test_basic_search(self, db_path: str):
        result = buddhi_search("parse_file", db_path)
        assert "parse_file" in result
        assert "--- START SYMBOL:" in result

    def test_returns_community_members(self, db_path: str):
        result = buddhi_search("parse_file", db_path)
        # walk_tree is in the same community as parse_file
        assert "walk_tree" in result

    def test_includes_bridges(self, db_path: str):
        result = buddhi_search("parse_file", db_path, include_bridges=True)
        # helper_util is connected via call edge (w=3.0) to parse_file
        assert "helper_util" in result

    def test_excludes_bridges_when_disabled(self, db_path: str):
        result = buddhi_search("parse_file", db_path, include_bridges=False)
        assert "helper_util" not in result

    def test_excludes_weak_bridges(self, db_path: str):
        result = buddhi_search("walk_tree", db_path, include_bridges=True)
        # DatabaseConnection is connected via reference (w=1.0) < threshold 3.0
        assert "DatabaseConnection" not in result

    def test_mode_signatures(self, db_path: str):
        result = buddhi_search("parse_file", db_path, mode="signatures")
        assert "parse_file" in result
        assert "--- START SYMBOL:" in result

    def test_mode_map(self, db_path: str):
        result = buddhi_search("parse_file", db_path, mode="map")
        assert "parse_file" in result
        assert "function_definition" in result

    def test_zero_hit_fallback(self, db_path: str):
        result = buddhi_search("xyzNonexistentThing", db_path)
        # Should trigger fallback and return file map
        assert "FILE MAP" in result or "parse_file" in result

    def test_budget_compression(self, db_path: str):
        # First, get unbounded result to know the full size
        full_result = buddhi_search("parse_file", db_path)
        full_len = len(full_result)

        # Set budget to half the full size — should trigger compression
        budget = full_len // 2
        compressed_result = buddhi_search("parse_file", db_path, budget=budget)

        # Compressed output should be smaller than full output
        assert len(compressed_result) < full_len
        # Should still contain the anchor node
        assert "parse_file" in compressed_result

    def test_empty_query(self, db_path: str):
        result = buddhi_search("", db_path)
        # Should trigger fallback to file map
        assert "FILE MAP" in result or len(result) > 0
