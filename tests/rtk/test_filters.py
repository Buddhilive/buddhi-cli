from __future__ import annotations

import json
from pathlib import Path

from buddhi.scripts.rtk.filters import (
    FilterSpec,
    find_matching_filter,
    load_filter_from_file,
)


def test_filter_spec_matching() -> None:
    spec = FilterSpec(
        name="pytest",
        match_command=r"^(?:uv\s+run\s+)?pytest\b",
    )
    assert spec.matches("pytest tests/")
    assert spec.matches("uv run pytest -v")
    assert not spec.matches("ruff check .")


def test_filter_spec_load_and_dump(tmp_path: Path) -> None:
    data = {
        "name": "sample-filter",
        "description": "A sample filter",
        "match_command": r"^sample\b",
        "strip_ansi": True,
        "strip_lines_matching": [r"^ok\b", r"^\s*$"],
        "keep_lines_matching": [r"^keep-me\b"],
        "max_lines": 50,
        "dedup": True,
        "tests": [
            {
                "name": "basic test",
                "input": "ok line\nkeep-me line\n",
                "expected": "keep-me line",
            }
        ],
    }

    file_path = tmp_path / "sample.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loaded = load_filter_from_file(file_path)
    assert loaded.name == "sample-filter"
    assert loaded.matches("sample run")
    assert loaded.is_strip_line("ok line")
    assert not loaded.is_strip_line("keep-me line")
    assert loaded.is_keep_line("keep-me line")


def test_find_matching_filter() -> None:
    f1 = FilterSpec(name="git", match_command=r"^git\s+status\b")
    f2 = FilterSpec(name="ruff", match_command=r"^ruff\b")

    match = find_matching_filter("git status", [f1, f2])
    assert match is not None
    assert match.name == "git"

    match_none = find_matching_filter("cargo build", [f1, f2])
    assert match_none is None
