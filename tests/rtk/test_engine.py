from __future__ import annotations

from buddhi.scripts.rtk.engine import apply_filter
from buddhi.scripts.rtk.filters import FilterSpec, ReplaceRule


def test_engine_strip_and_keep() -> None:
    spec = FilterSpec(
        name="test-strip",
        match_command="dummy",
        strip_lines_matching=[r"^INFO:\s+"],
        keep_lines_matching=[r"^INFO:\s+important"],
    )

    raw = "INFO: regular status\nINFO: important update\nNormal output\n"
    res = apply_filter(raw, spec)
    assert "INFO: important update" in res
    assert "Normal output" in res
    assert "INFO: regular status" not in res


def test_engine_never_drops_error_lines() -> None:
    spec = FilterSpec(
        name="test-error-guard",
        match_command="dummy",
        strip_lines_matching=[r".*"],  # Strips everything
    )

    raw = "regular line\nERROR: fatal breakdown\nanother regular line\n"
    res = apply_filter(raw, spec)
    assert "ERROR: fatal breakdown" in res
    assert "regular line" not in res


def test_engine_replace_rules() -> None:
    spec = FilterSpec(
        name="test-replace",
        match_command="dummy",
        replace_rules=[ReplaceRule(pattern=r"/long/path/to/project/", replacement="")],
    )

    raw = "File /long/path/to/project/main.py, line 10"
    res = apply_filter(raw, spec)
    assert res == "File main.py, line 10"


def test_engine_on_empty_fallback() -> None:
    spec = FilterSpec(
        name="test-empty",
        match_command="dummy",
        strip_lines_matching=[r".*"],
        on_empty="Everything clean.",
    )

    raw = "only noise lines\n"
    res = apply_filter(raw, spec)
    assert res == "Everything clean."


def test_engine_head_tail_limit() -> None:
    spec = FilterSpec(
        name="test-head-tail",
        match_command="dummy",
        max_lines=10,
        head_lines=3,
        tail_lines=3,
    )

    raw_lines = [f"line {i}" for i in range(30)]
    res = apply_filter("\n".join(raw_lines), spec)
    assert "line 0" in res
    assert "line 29" in res
    assert "lines omitted" in res
