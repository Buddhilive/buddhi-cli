from buddhi_ai.mcp.compression.ast_pruner import prune_signatures, extract_map


def test_prune_signatures_python():
    code = b"""
def my_function(a, b):
    print("hello")
    return a + b
    
class MyClass:
    def method(self):
        pass
"""
    pruned = prune_signatures("test.py", code)
    assert "# implementation hidden" in pruned
    assert "print" not in pruned
    assert "def my_function" in pruned
    assert "class MyClass:" in pruned


def test_extract_map_python():
    code = b"""
import os
from sys import path

def my_function(a, b):
    return a + b
    
class MyClass:
    def method(self):
        pass
"""
    mapped = extract_map("test.py", code)
    assert "import os" in mapped
    assert "from sys import path" in mapped
    assert "def my_function" in mapped
    assert "class MyClass" in mapped
    assert "return" not in mapped
