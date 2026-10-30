"""Generic fallback filter for RTK.

Applied when no command-specific filter matches, or when safe general reduction
is needed. Strips ANSI escapes, collapses blank lines, collapses consecutive duplicate lines,
preserves error lines, and applies head/tail truncation if output exceeds bounds.
"""

from __future__ import annotations

import re

ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
DEFAULT_GENERIC_MAX_LINES = 60
DEFAULT_HEAD_LINES = 25
DEFAULT_TAIL_LINES = 35

GENERIC_ERROR_PATTERNS = [
    re.compile(
        r"(?i)\b(error|fatal|fail|failed|failure|panic|exception|traceback|syntaxerror)\b"
    ),
    re.compile(r"^\s*File\s+\".*\",\s+line\s+\d+"),
    re.compile(r"^E\s{3,}.*"),
    re.compile(r"^>\s{3,}.*"),
]


def strip_ansi(text: str) -> str:
    """Remove ANSI color and escape sequences from text."""
    return ANSI_REGEX.sub("", text)


def is_error_line(line: str) -> bool:
    """Check if line matches any common failure/error signatures."""
    for pattern in GENERIC_ERROR_PATTERNS:
        if pattern.search(line):
            return True
    return False


def collapse_blank_lines(lines: list[str]) -> list[str]:
    """Collapse consecutive blank/whitespace-only lines to a single blank line."""
    result: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if not prev_blank:
                result.append("")
                prev_blank = True
        else:
            result.append(line)
            prev_blank = False
    return result


def collapse_duplicate_lines(lines: list[str]) -> list[str]:
    """Collapse consecutive identical lines into a single line with a repeat indicator."""
    if not lines:
        return []

    result: list[str] = []
    current_line = lines[0]
    count = 1

    for line in lines[1:]:
        if line == current_line and line.strip() != "":
            count += 1
        else:
            if count > 1:
                result.append(f"{current_line} [repeated {count} times]")
            else:
                result.append(current_line)
            current_line = line
            count = 1

    if count > 1:
        result.append(f"{current_line} [repeated {count} times]")
    else:
        result.append(current_line)

    return result


def apply_generic_filter(
    raw_output: str,
    max_lines: int = DEFAULT_GENERIC_MAX_LINES,
    head_lines: int = DEFAULT_HEAD_LINES,
    tail_lines: int = DEFAULT_TAIL_LINES,
) -> str:
    """Filter arbitrary command output using generic heuristics without losing error context."""
    if not raw_output:
        return ""

    cleaned = strip_ansi(raw_output)
    lines = cleaned.splitlines()

    lines = collapse_blank_lines(lines)
    lines = collapse_duplicate_lines(lines)

    if len(lines) <= max_lines:
        return "\n".join(lines).strip()

    # If exceeding max_lines, separate error lines so they are never lost
    head = lines[:head_lines]
    tail = lines[-tail_lines:] if tail_lines > 0 else []

    middle_lines = (
        lines[head_lines:-tail_lines] if tail_lines > 0 else lines[head_lines:]
    )
    omitted_count = len(middle_lines)

    # Collect any error lines that occurred in the omitted middle
    salvaged_errors: list[str] = []
    for line in middle_lines:
        if is_error_line(line):
            salvaged_errors.append(line)

    result_parts: list[str] = []
    result_parts.extend(head)

    omitted_notice = f"\n[... {omitted_count} lines omitted ...]\n"
    if salvaged_errors:
        omitted_notice += f"[... {len(salvaged_errors)} error/failure line(s) salvaged from omitted section: ...]\n"
        omitted_notice += "\n".join(salvaged_errors) + "\n"

    result_parts.append(omitted_notice.strip())
    result_parts.extend(tail)

    return "\n".join(result_parts).strip()
