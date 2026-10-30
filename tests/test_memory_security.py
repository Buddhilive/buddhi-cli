from pathlib import Path

import pytest

from buddhi.memory.security import (
    assert_no_secrets_in_tracked_memory,
    build_memory_file_path,
    parse_source_resource,
    resolve_and_sandbox_import,
    sanitize_slug,
)


def test_sanitize_slug() -> None:
    assert sanitize_slug("My Super Decision!") == "my-super-decision"
    assert sanitize_slug("CON") == "mem-con"
    assert sanitize_slug("aux") == "mem-aux"
    assert sanitize_slug("COM1") == "mem-com1"
    assert sanitize_slug("...bad...slug...") == "bad-slug"


def test_build_memory_file_path(tmp_path: Path) -> None:
    base = tmp_path / ".agents" / "memory"
    base.mkdir(parents=True)
    p = build_memory_file_path(base, "decision", "sqlite-wal")
    assert p == (base / "decisions" / "sqlite-wal.md").resolve()

    with pytest.raises(PermissionError):
        # Attempt traversal via slug
        build_memory_file_path(base, "decision", "../../evil")


def test_parse_source_resource(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    target_file = ws / "src" / "main.py"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("print('hello')\n", encoding="utf-8")

    path, start, end = parse_source_resource("src/main.py#L1-L10", ws)
    assert path == target_file.resolve()
    assert start == 1
    assert end == 10

    # Path traversal check
    with pytest.raises(PermissionError):
        parse_source_resource("../outside.py", ws)

    # Invalid line ranges
    with pytest.raises(ValueError):
        parse_source_resource("src/main.py#L10-L5", ws)


def test_resolve_and_sandbox_import(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    user = tmp_path / "user_memory"
    user.mkdir()
    doc = ws / "doc.md"
    doc.write_text("hello", encoding="utf-8")

    resolved = resolve_and_sandbox_import("@doc.md", ws, ws, user)
    assert resolved == doc.resolve()

    # Traversal outside roots
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(PermissionError):
        resolve_and_sandbox_import(f"@{outside}", ws, ws, user)


def test_assert_no_secrets_in_tracked_memory() -> None:
    clean = "This is a clean architectural note."
    assert_no_secrets_in_tracked_memory(clean, "project")

    with pytest.raises(PermissionError):
        assert_no_secrets_in_tracked_memory(
            "API_KEY = 'sk-proj-12345678901234567890123456789012'", "project"
        )

    with pytest.raises(PermissionError):
        assert_no_secrets_in_tracked_memory(
            "GITHUB_TOKEN = 'ghp_123456789012345678901234567890123456'", "project"
        )

    # Local scope permitted
    assert_no_secrets_in_tracked_memory(
        "API_KEY = 'sk-proj-12345678901234567890123456789012'", "local"
    )
