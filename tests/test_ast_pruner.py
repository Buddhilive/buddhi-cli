from __future__ import annotations

from buddhi.mcp.compression.ast_pruner import extract_map, prune_signatures


def test_prune_signatures_python():
    code = b"""def calculate(a: int, b: int) -> int:
    result = a + b
    return result

class MyClass:
    def __init__(self):
        self.x = 1

    def run(self):
        print(self.x)
"""
    pruned = prune_signatures("test.py", code)
    assert "def calculate(a: int, b: int) -> int:" in pruned
    assert "# implementation hidden" in pruned
    assert "return result" not in pruned
    assert "class MyClass:" in pruned
    assert "def __init__(self):" in pruned
    assert "def run(self):" in pruned


def test_extract_map_python():
    code = b"""import os
from pathlib import Path

def helper():
    return 42

class Service:
    def process(self):
        pass
"""
    extracted = extract_map("test.py", code)
    assert "import os" in extracted
    assert "from pathlib import Path" in extracted
    assert "def helper():" in extracted
    assert "# implementation hidden" in extracted
    assert "class Service:" in extracted
