# ruff: noqa: E402
import sys
import os
import json

# Add local mcp/ directory to sys.path so we can import db, parser, graph, server directly
_mcp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp")
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

import unittest
import unittest.mock
import tempfile
import shutil
from db import CodeGraphDB
from parser import ASTParser
from graph import CodeGraphAnalyzer
from indexer import CodeIndexer
from server import (
    get_codebase_summary_impl,
    find_relevant_symbols_impl,
    trace_impact_radius_impl,
    get_symbol_implementation_impl,
    execute_command_optimized_impl
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


class TestCodeIndexer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create a mock .buddhi folder in our temp_dir
        self.buddhi_dir = os.path.join(self.temp_dir, ".buddhi")
        os.makedirs(self.buddhi_dir, exist_ok=True)
        self.db_path = os.path.join(self.buddhi_dir, "graph.db")
        
        # Write a mock Python file to index
        self.mock_file = os.path.join(self.temp_dir, "mock_module.py")
        mock_code = """
class Worker:
    \"\"\"Represents a background worker.\"\"\"
    def work(self):
        print("working")

def run_worker():
    w = Worker()
    w.work()
"""
        with open(self.mock_file, "w", encoding="utf-8") as f:
            f.write(mock_code)
            
        self.indexer = CodeIndexer(workspace_root=self.temp_dir, db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_indexing_generates_visualization_files(self):
        # Index the codebase
        num_nodes, num_edges = self.indexer.index_codebase()
        
        # Verify indexing succeeded
        self.assertTrue(num_nodes > 0)
        
        # Verify visualization files exist
        json_path = os.path.join(self.buddhi_dir, "graph.json")
        html_path = os.path.join(self.buddhi_dir, "graph.html")
        
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(html_path))
        
        # 1. Verify JSON file contents
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertTrue(len(data["nodes"]) > 0)
        
        # Check that we have a class, method, and function
        types = [node["type"] for node in data["nodes"]]
        self.assertIn("class", types)
        self.assertIn("method", types)
        self.assertIn("function", types)
        
        # 2. Verify HTML file contents
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("vis.Network", html_content)
        self.assertIn("Interactive Legend", html_content)
        # Ensure the __EMBEDDED_GRAPH_JSON__ placeholder is replaced
        self.assertNotIn("__EMBEDDED_GRAPH_JSON__", html_content)
        # Ensure it contains the actual node data embedded
        self.assertIn("Worker", html_content)
        self.assertIn("run_worker", html_content)


class TestInitCommand(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    @unittest.mock.patch('os.getcwd')
    @unittest.mock.patch('server.index_codebase_impl')
    def test_init_creates_new_files(self, mock_index, mock_getcwd):
        mock_getcwd.return_value = self.temp_dir
        mock_index.return_value = "Successfully indexed 0 symbols."
        
        from cli.main import init_workspace
        
        init_workspace()
        
        # Check AGENTS.md was created
        agents_path = os.path.join(self.temp_dir, "AGENTS.md")
        self.assertTrue(os.path.exists(agents_path))
        with open(agents_path, "r", encoding="utf-8") as f:
            agents_content = f.read()
        self.assertIn("buddhi — Intelligent Codebase Index & Graph Layer", agents_content)
        
        # Check .agent/mcp_config.json was created
        mcp_path = os.path.join(self.temp_dir, ".agent", "mcp_config.json")
        self.assertTrue(os.path.exists(mcp_path))
        import json
        with open(mcp_path, "r", encoding="utf-8") as f:
            mcp_data = json.load(f)
        self.assertIn("buddhi-mcp", mcp_data["mcpServers"])
        self.assertEqual(mcp_data["mcpServers"]["buddhi-mcp"]["command"], "buddhi")
        self.assertEqual(mcp_data["mcpServers"]["buddhi-mcp"]["args"], ["mcp"])
        
        # Check indexing was called
        mock_index.assert_called_once_with(workspace_root=self.temp_dir)

    @unittest.mock.patch('os.getcwd')
    @unittest.mock.patch('server.index_codebase_impl')
    def test_init_merges_existing_files(self, mock_index, mock_getcwd):
        mock_getcwd.return_value = self.temp_dir
        mock_index.return_value = "Successfully indexed 0 symbols."
        
        # Create pre-existing AGENTS.md
        agents_path = os.path.join(self.temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write("# Existing Title\n\nSome old guidelines.")
            
        # Create pre-existing .agent/mcp_config.json with a custom server
        agent_dir = os.path.join(self.temp_dir, ".agent")
        os.makedirs(agent_dir, exist_ok=True)
        mcp_path = os.path.join(agent_dir, "mcp_config.json")
        existing_mcp = {
            "mcpServers": {
                "custom-server": {
                    "command": "custom",
                    "args": []
                }
            }
        }
        import json
        with open(mcp_path, "w", encoding="utf-8") as f:
            json.dump(existing_mcp, f)
            
        from cli.main import init_workspace
        init_workspace()
        
        # Verify AGENTS.md merged correctly
        with open(agents_path, "r", encoding="utf-8") as f:
            agents_content = f.read()
        self.assertIn("# Existing Title", agents_content)
        self.assertIn("buddhi — Intelligent Codebase Index & Graph Layer", agents_content)
        
        # Verify mcp_config.json merged correctly
        with open(mcp_path, "r", encoding="utf-8") as f:
            mcp_data = json.load(f)
        self.assertIn("custom-server", mcp_data["mcpServers"])
        self.assertIn("buddhi-mcp", mcp_data["mcpServers"])
        self.assertEqual(mcp_data["mcpServers"]["custom-server"]["command"], "custom")
        self.assertEqual(mcp_data["mcpServers"]["buddhi-mcp"]["command"], "buddhi")
        
        # Run init again to test block replacement and idempotency
        init_workspace()
        
        # Check that there is only one buddhi-mcp-owned block
        with open(agents_path, "r", encoding="utf-8") as f:
            new_agents_content = f.read()
        self.assertEqual(new_agents_content.count("<!-- buddhi-mcp-owned"), 1)

class TestMCPCommandInterceptor(unittest.TestCase):
    def test_shell_execution_success(self):
        # Run a simple echo command and verify returncode is 0 and output parsed
        res_json_str = execute_command_optimized_impl("echo test_interceptor_success")
        import json
        res_data = json.loads(res_json_str)
        
        self.assertIn("status", res_data)
        self.assertIn("summary", res_data)
        self.assertIn("critical_findings", res_data)
        self.assertEqual(res_data["exit_code"], 0)
        self.assertEqual(res_data["status"], "success")

    def test_shell_execution_failure(self):
        # Run a failing command (e.g. exit 1 or a non-existent command)
        command = "non_existent_command_xyz_123"
        res_json_str = execute_command_optimized_impl(command)
        import json
        res_data = json.loads(res_json_str)
        
        self.assertIn("status", res_data)
        self.assertNotEqual(res_data["exit_code"], 0)
        self.assertEqual(res_data["status"], "error")
        # Ensure it captured the error or warning in findings
        self.assertTrue(len(res_data["critical_findings"]) > 0)

    @unittest.mock.patch('urllib.request.urlopen')
    def test_api_integration_success(self, mock_urlopen):
        import json
        # Mock successful API call returning valid OpenAI-compatible ResponseOutput
        mock_response = unittest.mock.MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": "res-123",
            "object": "response",
            "status": "completed",
            "output": [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "status": "success",
                                "summary": "Custom mock API response summary",
                                "critical_findings": ["All looks green from mock"],
                                "exit_code": 0
                            })
                        }
                    ]
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute command - should hit the mock API
        res_json_str = execute_command_optimized_impl("echo test_api")
        res_data = json.loads(res_json_str)
        
        self.assertEqual(res_data["status"], "success")
        self.assertEqual(res_data["summary"], "Custom mock API response summary")
        self.assertEqual(res_data["critical_findings"], ["All looks green from mock"])
        self.assertEqual(res_data["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
