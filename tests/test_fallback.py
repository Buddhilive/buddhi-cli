import json
from pathlib import Path
import pytest
from buddhi_ai.mcp.tools.read import execute_buddhi_read
from buddhi_ai.search.search import buddhi_search

@pytest.fixture(autouse=True)
def clean_buddhi_dir():
    # Setup clean environment
    buddhi_dir = Path(".buddhi")
    fallback_file = buddhi_dir / "fallback_allowed.json"
    if fallback_file.exists():
        fallback_file.unlink()
    yield
    if fallback_file.exists():
        fallback_file.unlink()

def test_buddhi_read_query_fallback():
    # Verify execute_buddhi_read queries glob recursively as a fallback
    # Let's search for "test_fallback.py" which definitely exists in the workspace
    result = execute_buddhi_read(query="test_fallback.py", db_path=None)
    assert "Found" in result
    assert "test_fallback.py" in result
    assert "native fallback" in result

def test_buddhi_read_query_not_found_fallback_state():
    # Verify execute_buddhi_read writes fallback allowance file on missing matches
    result = execute_buddhi_read(query="nonexistent_file_name_xyz.txt", db_path=None)
    assert "Error" in result
    
    fallback_file = Path(".buddhi/fallback_allowed.json")
    assert fallback_file.exists()
    
    with open(fallback_file, "r") as f:
        allowed = json.load(f)
    assert allowed.get("find_by_name") is True

def test_buddhi_search_fallback():
    # Verify buddhi_search falls back to native grep when BM25 yields 0 anchors
    # We search for "test_buddhi_search_fallback" in tests/test_fallback.py itself!
    result = buddhi_search("test_buddhi_search_fallback", db_path="nonexistent_db.db")
    assert "Native Grep Fallback Matches" in result
    assert "test_fallback.py" in result

def test_buddhi_search_fallback_not_found_state():
    # Verify buddhi_search writes fallback state when query is completely absent
    query = "completely_nonexistent_" + "pattern_xyz_123"
    result = buddhi_search(query, db_path="nonexistent_db.db")
    assert "Error" in result
    
    fallback_file = Path(".buddhi/fallback_allowed.json")
    assert fallback_file.exists()
    
    with open(fallback_file, "r") as f:
        allowed = json.load(f)
    assert allowed.get("grep_search") is True
