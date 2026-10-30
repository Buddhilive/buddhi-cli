from pathlib import Path

from buddhi.memory.resolver import matches_active_files, resolve_imports


def test_matches_active_files() -> None:
    # Empty patterns = match everything (global)
    assert matches_active_files([], ["src/api/views.py"])
    assert matches_active_files([], [])

    patterns = ["src/buddhi/mcp/**/*.py", "tests/**"]
    assert matches_active_files(patterns, ["src/buddhi/mcp/server.py"])
    assert matches_active_files(patterns, ["tests/test_model.py"])
    assert not matches_active_files(patterns, ["src/buddhi/graph/builder.py"])


def test_resolve_imports_recursive_and_cycle(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    user = tmp_path / "user"
    user.mkdir()

    # File A imports File B
    file_b = ws / "b.md"
    file_b.write_text("# Section B\nContent from B.", encoding="utf-8")

    file_a = ws / "a.md"
    file_a.write_text("# Section A\n@b.md\nEnd of A.", encoding="utf-8")

    expanded = resolve_imports(file_a.read_text(encoding="utf-8"), file_a, ws, user)
    assert "# Section B" in expanded
    assert "Content from B." in expanded
    assert "End of A." in expanded

    # Circular import test: B imports A
    file_b.write_text("# Section B\n@a.md", encoding="utf-8")
    expanded_cycle = resolve_imports(
        file_a.read_text(encoding="utf-8"), file_a, ws, user
    )
    assert "@import-cycle-detected" in expanded_cycle

    # Depth exceeded test (6 levels deep)
    current = ws / "step0.md"
    current.write_text("depth 0", encoding="utf-8")
    for i in range(1, 8):
        nxt = ws / f"step{i}.md"
        nxt.write_text(f"@step{i - 1}.md", encoding="utf-8")

    deepest = ws / "step7.md"
    deep_expanded = resolve_imports(
        deepest.read_text(encoding="utf-8"), deepest, ws, user, max_depth=5
    )
    assert "@import-depth-exceeded" in deep_expanded
