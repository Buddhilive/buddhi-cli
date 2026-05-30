"""
Phase 1 — Smart Filtering (Noise Eradication).

Strips visual noise from raw shell output:
  1. ANSI escape sequence removal (color codes, cursor movement).
  2. Progress bar collapse (carriage-return overwriting lines, spinner chars).
  3. Whitespace & CJK normalization (excessive blanks, garbled UTF-8 floods).
"""

import re
import unicodedata

# ── 1. ANSI Escape Sequences ─────────────────────────────────────────────────
# Matches CSI sequences (ESC[...m), OSC sequences (ESC]...ST/BEL), and lone ESC.
_ANSI_RE = re.compile(
    r"""
    \x1b          # ESC
    (?:
        \[[0-9;]*[A-Za-z]   # CSI: ESC [ ... letter  (colors, movement)
      | \][^\x07\x1b]*(?:\x07|\x1b\\)  # OSC: ESC ] ... BEL or ST
      | [^[\]]            # Two-char ESC sequences
    )
    | \x1b          # bare lone ESC
    """,
    re.VERBOSE,
)


def strip_ansi(text: str) -> str:
    """Remove all ANSI / VT100 escape sequences from *text*."""
    return _ANSI_RE.sub("", text)


# ── 2. Progress Bar & Spinner Collapse ───────────────────────────────────────
# Spinner characters used by common CLI tools (npm, yarn, cargo, pip …)
_SPINNER_CHARS: frozenset[str] = frozenset("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏◐◓◑◒|/-\\⣾⣽⣻⢿⡿⣟⣯⣷")

# Patterns that strongly indicate a progress bar line:
# - Contains \r (carriage return used for in-place rewrite)
# - Heavy repetition of `=`, `-`, `#`, `*`, `.` filling ≥ 8 chars
# - Spinner characters
_PROGRESS_BAR_RE = re.compile(
    r"""
    (?:                         # carriage-return variant
        [^\n]*\r[^\n]*
    )
    |
    (?:                         # ASCII fill bars  [=====>   ] / [#######   ]
        \[(?:[=\-#.*>◼◻░▒█ ]{8,})\]
    )
    |
    (?:                         # percentage + filler (e.g. "  47% |████░░|")
        \d{1,3}\s*%\s*[|│][\s\S]{0,60}[|│]
    )
    """,
    re.VERBOSE,
)

# How many consecutive percentage matches before we collapse
_PERCENTAGE_REPEAT_RE = re.compile(r"\b\d{1,3}%\b")


def _is_progress_line(line: str) -> bool:
    """Return True if *line* looks like a transient progress bar."""
    stripped = line.strip()
    if not stripped:
        return False
    # Carriage return: classic in-place overwrite
    if "\r" in stripped:
        return True
    # Heavy ASCII fill bar
    if _PROGRESS_BAR_RE.search(stripped):
        return True
    # Spinner characters dominate line
    spinner_count = sum(1 for ch in stripped if ch in _SPINNER_CHARS)
    if spinner_count > 0 and spinner_count / max(len(stripped), 1) > 0.15:
        return True
    return False


def collapse_progress_bars(text: str) -> str:
    """Remove progress-bar and spinner lines from *text*."""
    lines = text.splitlines()
    clean: list[str] = []
    for line in lines:
        if not _is_progress_line(line):
            clean.append(line)
    return "\n".join(clean)


# ── 3. Whitespace & CJK Normalization ────────────────────────────────────────
# Maximum consecutive blank lines allowed in the output
_MAX_BLANK_LINES = 1

# Detects runs of high-codepoint symbols that indicate garbled encoding
# (blocks of box-drawing, Braille, or private-use chars flooding a line)
_GARBLED_LINE_RE = re.compile(
    r"^[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2400-\u27ff\ue000-\uf8ff]{6,}$"
)


def _is_garbled(line: str) -> bool:
    """Return True if the line is dominated by control / private-use chars."""
    stripped = line.strip()
    if not stripped:
        return False
    # Count characters outside printable ASCII + common Unicode text ranges
    garbage_chars = sum(
        1
        for ch in stripped
        if unicodedata.category(ch) in {"Cc", "Cs", "Co"}
    )
    ratio = garbage_chars / max(len(stripped), 1)
    return ratio > 0.5


def normalize_whitespace(text: str) -> str:
    """
    Collapse multiple blank lines to at most one, and drop garbled symbol floods.
    """
    lines = text.splitlines()
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if _is_garbled(line):
            continue
        if line.strip() == "":
            blank_count += 1
            if blank_count <= _MAX_BLANK_LINES:
                result.append("")
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result)


# ── Public API ────────────────────────────────────────────────────────────────

def apply(text: str) -> str:
    """Run the full Phase 1 noise-eradication pipeline on *text*.

    Order matters:
        1. Strip ANSI first (so downstream regex only sees printable chars).
        2. Collapse progress bars.
        3. Normalize whitespace and remove garbled lines.
    """
    text = strip_ansi(text)
    text = collapse_progress_bars(text)
    text = normalize_whitespace(text)
    return text
