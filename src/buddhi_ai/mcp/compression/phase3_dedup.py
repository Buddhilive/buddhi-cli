"""
Phase 3 — Structural Deduplication (Rabin-Karp Rolling Hash).

Detects consecutive repeated blocks of lines and collapses them into a
compact summary. Falls back to exact-string matching for very short blocks.

Algorithm:
  - Slide a window of W=3 lines across the output.
  - For each window position compute a rolling Rabin-Karp hash.
  - On a hash collision verify byte-exact equality.
  - Count consecutive repetitions and replace with a placeholder.
"""

from __future__ import annotations

# Rabin-Karp parameters
_RK_BASE: int = 31
_RK_MOD: int = (1 << 61) - 1  # Mersenne prime

# Window sizes to try, in descending order of preference.
# A larger window means fewer false collapses on semantically different content.
_WINDOW_SIZES: tuple[int, ...] = (5, 4, 3)

# Minimum number of repetitions before we collapse
_MIN_REPEATS: int = 2


def _rk_hash(lines: list[str]) -> int:
    """Compute a Rabin-Karp polynomial hash for a list of *lines*."""
    h = 0
    for line in lines:
        for ch in line:
            h = (h * _RK_BASE + ord(ch)) % _RK_MOD
        # Use newline as separator between lines
        h = (h * _RK_BASE + ord("\n")) % _RK_MOD
    return h


def _collapse_with_window(lines: list[str], window: int) -> list[str]:
    """Try to collapse repetitions using a given *window* size."""
    n = len(lines)
    if n < window * _MIN_REPEATS:
        return lines

    result: list[str] = []
    i = 0

    while i <= n - window:
        block = lines[i : i + window]
        h = _rk_hash(block)

        # Count how many consecutive times this block repeats
        repeat_count = 1
        j = i + window
        while j + window <= n:
            candidate = lines[j : j + window]
            if _rk_hash(candidate) == h and candidate == block:
                repeat_count += 1
                j += window
            else:
                break

        if repeat_count >= _MIN_REPEATS:
            # Emit first occurrence, then a collapsed marker, then last occurrence
            result.extend(block)
            if repeat_count > 2:
                result.append(
                    f"... [Previous block repeated {repeat_count - 2} more time(s)] ..."
                )
            if repeat_count > 1:
                result.extend(block)  # emit last occurrence
            i = j
        else:
            result.append(lines[i])
            i += 1

    # Append any remaining tail lines
    result.extend(lines[i:])
    return result


def apply(text: str) -> str:
    """Collapse consecutive repeated structural blocks in *text*.

    Tries window sizes from largest to smallest and applies the first one
    that achieves any collapse. Returns the deduplicated text.
    """
    lines = text.splitlines()
    original_count = len(lines)

    for window in _WINDOW_SIZES:
        collapsed = _collapse_with_window(lines, window)
        if len(collapsed) < original_count:
            # Collapse achieved — return result
            return "\n".join(collapsed)

    # No repetitions found at any window size — return original
    return text
