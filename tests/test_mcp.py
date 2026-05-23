# ruff: noqa: E402
import sys
import os

# Add local mcp/ directory to sys.path so we can import db, parser, graph, server directly
_mcp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp")
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

import unittest
import tempfile
import shutil
from db import CodeGraphDB
from parser import ASTParser
from graph import CodeGraphAnalyzer
from server import (
    get_codebase_summary_impl,
    find_relevant_symbols_impl,
    trace_impact_radius_impl,
    get_symbol_implementation_impl
)

class TestCodeGraphDB(unittest.TestCase):
    def setUp(self):
        # Create a temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "graph_test.db")
        self.db = CodeGraphDB(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_database_initialization(self):
        # Check that tables exist by running basic queries
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]
            self.assertIn("nodes", tables)
            self.assertIn("edges", tables)
            self.assertIn("nodes_fts", tables)

    def test_insert_and_fts_search(self):
        nodes = [
            {
                "id": "file.py::func_a",
                "name": "func_a",
                "type": "function",
                "file_path": "file.py",
                "start_line": 10,
                "end_line": 15,
                "docstring": "Handles JWT authentication verification."
            },
            {
                "id": "file.py::func_b",
                "name": "func_b",
                "type": "function",
                "file_path": "file.py",
                "start_line": 20,
                "end_line": 25,
                "docstring": "Fetches a user session from cache."
            }
        ]
        self.db.insert_nodes(nodes)
        
        # Test finding all
        all_nodes = self.db.get_all_nodes()
        self.assertEqual(len(all_nodes), 2)
        
        # Test full-text search
        results = self.db.find_relevant_symbols("JWT")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["symbol"]["name"], "func_a")

    def test_impact_radius_cte(self):
        # Build Caller Chain: func_c -> calls -> func_b -> calls -> func_a
        nodes = [
            {"id": "c.py::func_c", "name": "func_c", "type": "function", "file_path": "c.py", "start_line": 1, "end_line": 5, "docstring": ""},
            {"id": "b.py::func_b", "name": "func_b", "type": "function", "file_path": "b.py", "start_line": 1, "end_line": 5, "docstring": ""},
            {"id": "a.py::func_a", "name": "func_a", "type": "function", "file_path": "a.py", "start_line": 1, "end_line": 5, "docstring": ""}
        ]
        edges = [
            {"source": "b.py::func_b", "target": "a.py::func_a", "type": "calls"},
            {"source": "c.py::func_c", "target": "b.py::func_b", "type": "calls"}
        ]
        
        self.db.insert_nodes(nodes)
        self.db.insert_edges(edges)

        # Trace upstream from func_a
        impact = self.db.trace_impact_radius("a.py::func_a", max_depth=3)
        self.assertEqual(len(impact), 2)
        
        # Depth 1 caller should be func_b
        depth_1 = [n for n in impact if n["depth"] == 1]
        self.assertEqual(len(depth_1), 1)
        self.assertEqual(depth_1[0]["name"], "func_b")

        # Depth 2 caller should be func_c
        depth_2 = [n for n in impact if n["depth"] == 2]
        self.assertEqual(len(depth_2), 1)
        self.assertEqual(depth_2[0]["name"], "func_c")


class TestASTParser(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.parser = ASTParser(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_python_parsing(self):
        code = """
import os
from math import sqrt

class Calculator:
    \"\"\"Performs basic calculations.\"\"\"
    def add(self, a, b):
        return a + b

def calculate_hypotenuse(x, y):
    \"\"\"Calculates distance.\"\"\"
    h = sqrt(x*x + y*y)
    return h
"""
        rel_path = "math_util.py"
        with open(os.path.join(self.temp_dir, rel_path), "w", encoding="utf-8") as f:
            f.write(code)

        result = self.parser.parse_file(rel_path)
        symbols = result["symbols"]
        imports = result["imports"]
        _calls = result["calls"]

        # Check symbols: Module, Class, Method, Function
        symbol_types = [s["type"] for s in symbols]
        self.assertIn("module", symbol_types)
        self.assertIn("class", symbol_types)
        self.assertIn("method", symbol_types)
        self.assertIn("function", symbol_types)

        # Check specific names
        names = [s["name"] for s in symbols]
        self.assertIn("Calculator", names)
        self.assertIn("add", names)
        self.assertIn("calculate_hypotenuse", names)

        # Check imports mapped
        self.assertIn("os", imports)
        self.assertEqual(imports["os"]["module"], "os")
        self.assertIn("sqrt", imports)
        self.assertEqual(imports["sqrt"]["module"], "math")
        self.assertEqual(imports["sqrt"]["name"], "sqrt")


class TestCodeGraphAnalyzer(unittest.TestCase):
    def test_community_detection(self):
        analyzer = CodeGraphAnalyzer()
        # Create a disconnected bipartite structure
        nodes = [
            {"id": "a1"}, {"id": "a2"}, {"id": "a3"},
            {"id": "b1"}, {"id": "b2"}, {"id": "b3"}
        ]
        # Cluster A: a1<->a2<->a3, Cluster B: b1<->b2<->b3
        edges = [
            {"source": "a1", "target": "a2", "type": "calls"},
            {"source": "a2", "target": "a3", "type": "calls"},
            {"source": "b1", "target": "b2", "type": "calls"},
            {"source": "b2", "target": "b3", "type": "calls"}
        ]
        
        community_mappings = analyzer.compute_communities(nodes, edges)
        
        # Verify both clusters exist and separate
        self.assertEqual(community_mappings["a1"], community_mappings["a2"])
        self.assertEqual(community_mappings["b1"], community_mappings["b2"])
        self.assertNotEqual(community_mappings["a1"], community_mappings["b1"])


class TestMCPTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "graph_tools.db")
        self.db = CodeGraphDB(self.db_path)

        # Insert some nodes
        self.nodes = [
            {
                "id": "app.py::heavy_func",
                "name": "heavy_func",
                "type": "function",
                "file_path": "app.py",
                "start_line": 1,
                "end_line": 200,  # 200 lines -> Massive Object
                "docstring": "Calculates planetary trajectories."
            },
            {
                "id": "app.py::short_func",
                "name": "short_func",
                "type": "function",
                "file_path": "app.py",
                "start_line": 203,
                "end_line": 205,
                "docstring": "Basic helper."
            }
        ]
        self.db.insert_nodes(self.nodes)

        # Write mock app.py
        with open(os.path.join(self.temp_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("def heavy_func():\n    pass\n" + "\n" * 200 + "\ndef short_func():\n    return 42\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_summary_and_search_mcp_output(self):
        # Summary
        summary = get_codebase_summary_impl(self.db_path)
        self.assertIn("Community", summary)

        # Search
        search = find_relevant_symbols_impl("planetary", self.db_path)
        self.assertIn("heavy_func", search)

    def test_guardrail_massive_object(self):
        # Test short func - should return implementation
        short_res = get_symbol_implementation_impl(
            "app.py::short_func",
            max_lines=150,
            db_path=self.db_path,
            workspace_root=self.temp_dir
        )
        self.assertIn("return 42", short_res)
        self.assertNotIn("Massive Object Guardrail Triggered", short_res)

        # Test heavy func - should trigger guardrail
        heavy_res = get_symbol_implementation_impl(
            "app.py::heavy_func",
            max_lines=150,
            db_path=self.db_path,
            workspace_root=self.temp_dir
        )
        self.assertIn("Massive Object Guardrail Triggered", heavy_res)
        self.assertNotIn("return 42", heavy_res)


if __name__ == "__main__":
    unittest.main()
