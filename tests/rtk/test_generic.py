from __future__ import annotations

from buddhi.scripts.rtk.generic import (
    apply_generic_filter,
    collapse_blank_lines,
    collapse_duplicate_lines,
    strip_ansi,
)


def test_strip_ansi() -> None:
    ansi_text = "\x1b[31mRed Error\x1b[0m \x1b[1;32mGreen\x1b[0m"
    assert strip_ansi(ansi_text) == "Red Error Green"


def test_collapse_blank_lines() -> None:
    lines = ["line 1", "", "   ", "", "line 2", "", "line 3"]
    collapsed = collapse_blank_lines(lines)
    assert collapsed == ["line 1", "", "line 2", "", "line 3"]


def test_collapse_duplicate_lines() -> None:
    lines = ["polling...", "polling...", "polling...", "ready"]
    collapsed = collapse_duplicate_lines(lines)
    assert collapsed == ["polling... [repeated 3 times]", "ready"]


def test_generic_filter_preserves_errors_in_truncated_middle() -> None:
    raw_lines = [f"info line {i}" for i in range(100)]
    # Inject an error line in the middle section (between line 25 and 65)
    raw_lines[50] = "CRITICAL: Traceback (most recent call last): failed!"
    raw = "\n".join(raw_lines)

    filtered = apply_generic_filter(raw, max_lines=40, head_lines=15, tail_lines=15)
    assert "lines omitted" in filtered
    assert "Traceback" in filtered
    assert "failed!" in filtered


def test_generic_filter_short_output() -> None:
    raw = "hello\nworld"
    assert apply_generic_filter(raw) == "hello\nworld"
