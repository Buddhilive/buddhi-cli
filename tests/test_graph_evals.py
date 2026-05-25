import os
import sys
import unittest
import tempfile
import shutil

# Add local mcp/ directory to sys.path
_mcp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp")
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

from indexer import CodeIndexer
from db import CodeGraphDB

class TestGraphEvals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Build the AST SQLite DB on-the-fly for tests/fixtures."""
        cls.test_dir = os.path.dirname(os.path.abspath(__file__))
        cls.fixtures_dir = os.path.join(cls.test_dir, "fixtures")
        
        # Temp dir for database
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "fixtures_graph.db")
        
        # Initialize the indexer on the fixtures directory
        cls.indexer = CodeIndexer(workspace_root=cls.fixtures_dir, db_path=cls.db_path)
        cls.indexer.index_codebase()
        
        # We hold a reference to the built database
        cls.db = CodeGraphDB(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def test_find_relevant_symbols_invariant(self):
        """Assert find_relevant_symbols returns exactly expected definitions for mock classes."""
        # 'ProcessManager' is inside mock_python/main.py
        results = self.db.find_relevant_symbols("ProcessManager")
        self.assertTrue(len(results) > 0, "Should find ProcessManager")
        
        found_names = [res["symbol"]["name"] for res in results]
        self.assertIn("ProcessManager", found_names)
        
        # Ensure 'compute_score' is found
        results_score = self.db.find_relevant_symbols("compute_score")
        found_score_names = [res["symbol"]["name"] for res in results_score]
        self.assertIn("compute_score", found_score_names)

    def test_trace_impact_radius_invariant(self):
        """Validate recursive upstream caller mapping."""
        # Find the node ID for `compute_score`
        results = self.db.find_relevant_symbols("compute_score")
        self.assertTrue(len(results) > 0)
        compute_score_node_id = results[0]["symbol"]["id"]
        
        # Trace impact radius for compute_score (who calls compute_score?)
        # `run_process` calls `compute_score`
        impact = self.db.trace_impact_radius(compute_score_node_id, max_depth=2)
        
        # We expect at least `run_process` to be in the impact list
        caller_names = [node["name"] for node in impact]
        self.assertIn("run_process", caller_names)
        
    def test_get_symbol_implementation_guardrail(self):
        """Verify the guardrails fallback to signature when exceeding max_lines."""
        results = self.db.find_relevant_symbols("ProcessManager")
        self.assertTrue(len(results) > 0)
        manager_node_id = results[0]["symbol"]["id"]
        
        # Use server.py's implementation which includes the guardrail
        from server import get_symbol_implementation_impl
        
        # Assuming ProcessManager is very short, we artificially lower the limit to 2 lines to trigger guardrail
        res = get_symbol_implementation_impl(manager_node_id, max_lines=2, db_path=self.db_path, workspace_root=self.fixtures_dir)
        
        self.assertIn("Massive Object Guardrail Triggered", res)

if __name__ == "__main__":
    unittest.main()
