from __future__ import annotations

from pathlib import Path
from buddhi.mcp.compression.classifier import resolve_mode


def test_classifier_intent_editing():
    assert resolve_mode("file.py", "Please fix the bug in this file") == "full"
    assert resolve_mode("file.py", "Refactor the authentication module") == "full"
    assert resolve_mode("file.py", "Add a new feature") == "full"
    assert resolve_mode("file.py", "Implement search tool") == "full"


def test_classifier_intent_mapping():
    assert resolve_mode("file.py", "Show me the architecture and imports") == "map"
    assert resolve_mode("file.py", "Map out the dependencies") == "map"
    assert resolve_mode("file.py", "Show module exports and linkages") == "map"


def test_classifier_intent_read_only():
    assert resolve_mode("file.py", "Find references and understand the call flow") == "signatures"
    assert resolve_mode("file.py", "Give me an overview of the interface") == "signatures"
    assert resolve_mode("file.py", "Trace how this function works") == "signatures"


def test_classifier_file_size_fallback(tmp_path: Path):
    small_file = tmp_path / "small.py"
    small_file.write_text("x = 1\n")
    assert resolve_mode(str(small_file), None) == "full"

    large_file = tmp_path / "large.py"
    large_file.write_text("a = 1\n" * 1500)
    assert resolve_mode(str(large_file), None) == "signatures"
