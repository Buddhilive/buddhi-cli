from pathlib import Path

from buddhi.memory.hash import compute_content_hash, verify_source_staleness
from buddhi.memory.models import MemorySource


def test_compute_content_hash_line_slicing(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    code_file = ws / "module.py"
    code_file.write_text("line 1\nline 2\nline 3\nline 4\nline 5\n", encoding="utf-8")

    # Hash full file
    hash_full = compute_content_hash(ws, "module.py")
    assert len(hash_full) == 64

    # Hash slice L2-L3 ("line 2\nline 3\n")
    hash_slice = compute_content_hash(ws, "module.py#L2-L3")
    assert len(hash_slice) == 64
    assert hash_slice != hash_full


def test_staleness_detection(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    code_file = ws / "module.py"
    code_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    initial_hash = compute_content_hash(ws, "module.py#L2-L2")
    source = MemorySource(
        id="src", resource="module.py#L2-L2", content_hash=initial_hash
    )

    # Initial check: not stale
    res = verify_source_staleness(ws, source)
    assert not res.is_stale

    # Mutate line 1 (outside slice): should still NOT be stale
    code_file.write_text("MODIFIED line 1\nline 2\nline 3\n", encoding="utf-8")
    res = verify_source_staleness(ws, source)
    assert not res.is_stale

    # Mutate line 2 (inside slice): should become stale
    code_file.write_text("MODIFIED line 1\nMODIFIED line 2\nline 3\n", encoding="utf-8")
    res = verify_source_staleness(ws, source)
    assert res.is_stale
    assert res.reason == "hash_mismatch"

    # Delete file: should report file_not_found
    code_file.unlink()
    res = verify_source_staleness(ws, source)
    assert res.is_stale
    assert res.reason == "file_not_found"
