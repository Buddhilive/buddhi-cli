from buddhi_ai.mcp.compression.classifier import resolve_mode
import tempfile
import os


def test_resolve_mode_with_intent():
    assert resolve_mode("test.py", "Please fix the bug here") == "full"
    assert resolve_mode("test.py", "What are the dependencies?") == "map"
    assert resolve_mode("test.py", "Trace the call flow") == "signatures"


def test_resolve_mode_fallback_small_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"a" * 1024) # 1KB file
        temp_path = f.name
        
    try:
        assert resolve_mode(temp_path) == "full"
    finally:
        os.remove(temp_path)


def test_resolve_mode_fallback_large_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"a" * 5000) # 5KB file
        temp_path = f.name
        
    try:
        assert resolve_mode(temp_path) == "signatures"
    finally:
        os.remove(temp_path)


def test_resolve_mode_missing_file():
    assert resolve_mode("does_not_exist.py") == "signatures"
