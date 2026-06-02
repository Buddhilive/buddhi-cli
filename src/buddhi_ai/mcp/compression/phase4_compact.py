"""
Phase 4 — Compact Response Protocol (CRP) Layout.

Transforms processed text into a token-dense dialect:
  1. Delta-only formatting: replace verbose change language with +/-/~ symbols.
  2. Identifier mapping: detect repeated long path prefixes, assign $DIR_n vars.
  3. Exact token verification via tiktoken; hard-truncate if still over budget.
"""

from __future__ import annotations

import re
from collections import Counter

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")

# ── Constants ─────────────────────────────────────────────────────────────────
# Minimum path length to be eligible for replacement ($DIR_n)
_MIN_PATH_LEN: int = 20
# Minimum occurrences for a path prefix to earn its own variable
_MIN_PATH_OCCURRENCES: int = 3
# Hard truncation: keep this many leading / trailing lines when over budget
_HEAD_LINES: int = 100
_TAIL_LINES: int = 50


def count_tokens(text: str) -> int:
    """Return the tiktoken token count for *text* using cl100k_base."""
    return len(_ENCODING.encode(text))


# ── 1. Delta-Only Formatting ─────────────────────────────────────────────────

# Verbose phrases → compact symbol replacements
_DELTA_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\badded\b", re.I), "+"),
    (re.compile(r"\binserted\b", re.I), "+"),
    (re.compile(r"\bcreated\b", re.I), "+"),
    (re.compile(r"\bremoved\b", re.I), "-"),
    (re.compile(r"\bdeleted\b", re.I), "-"),
    (re.compile(r"\bdropped\b", re.I), "-"),
    (re.compile(r"\bmodified\b", re.I), "~"),
    (re.compile(r"\bupdated\b", re.I), "~"),
    (re.compile(r"\bchanged\b", re.I), "~"),
    (re.compile(r"\brenamed\b", re.I), "~"),
]


def apply_delta_format(text: str) -> str:
    """Replace verbose change verbs with +/-/~ symbols."""
    for pattern, symbol in _DELTA_REPLACEMENTS:
        text = pattern.sub(symbol, text)
    return text


# ── 2. Identifier Mapping ────────────────────────────────────────────────────

# Matches Unix-style absolute paths (and Windows-style) with at least one sub-dir
_PATH_RE = re.compile(r"(?:/[\w.\-]+){3,}/?|(?:[A-Za-z]:\\[\w\\ .\-]+\\){2,}")


def _extract_common_prefixes(text: str) -> list[tuple[str, int]]:
    """Find directory paths that repeat often enough to warrant a variable."""
    matches = _PATH_RE.findall(text)
    if not matches:
        return []

    # Gather all parent-directory prefixes for each match
    prefix_counts: Counter[str] = Counter()
    for path in matches:
        # Walk up the directory hierarchy
        parts = path.rstrip("/\\").split("/") if "/" in path else path.rstrip("\\").split("\\")
        for depth in range(2, len(parts)):
            prefix = ("/".join(parts[:depth]) + "/") if "/" in path else ("\\".join(parts[:depth]) + "\\")
            if len(prefix) >= _MIN_PATH_LEN:
                prefix_counts[prefix] += 1

    eligible = [
        (prefix, count)
        for prefix, count in prefix_counts.items()
        if count >= _MIN_PATH_OCCURRENCES
    ]
    # Sort longest prefix first so more specific matches win
    eligible.sort(key=lambda x: -len(x[0]))
    return eligible


def apply_identifier_mapping(text: str) -> str:
    """
    Replace repeated long directory prefixes with short $DIR_n variables.
    Prepends a mapping table header to the output.
    """
    prefixes = _extract_common_prefixes(text)
    if not prefixes:
        return text

    mapping_lines: list[str] = ["[PATH ALIASES]"]
    for idx, (prefix, _) in enumerate(prefixes, start=1):
        var = f"$DIR_{idx}"
        mapping_lines.append(f"  {var} = {prefix}")
        text = text.replace(prefix, var)

    header = "\n".join(mapping_lines) + "\n" + ("-" * 40) + "\n"
    return header + text


# ── 3. Token Budget Enforcement ───────────────────────────────────────────────

_NOTICE_TEMPLATE = "\n... [buddhi_shell: Output truncated — {omitted} lines omitted to fit token budget ({budget})] ...\n"
# Reserve tokens for the truncation notice itself
_NOTICE_OVERHEAD: int = 25


def _fit_lines(lines: list[str], token_limit: int) -> list[str]:
    """Binary search the longest prefix of *lines* that fits within *token_limit* tokens."""
    if not lines:
        return []
    lo, hi = 0, len(lines)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if count_tokens("\n".join(lines[:mid])) <= token_limit:
            lo = mid
        else:
            hi = mid - 1
    return lines[:lo]


def enforce_budget(text: str, budget: int) -> str:
    """Hard-truncate *text* if it exceeds *budget* tokens.

    Proportionally allocates 2/3 of the remaining budget to a head segment and
    1/3 to a tail segment so that both context and exit codes are preserved.
    Works correctly for both tiny budgets (e.g. 100 tokens) and large ones.
    """
    if budget <= 0 or count_tokens(text) <= budget:
        return text

    lines = text.splitlines()
    usable = max(0, budget - _NOTICE_OVERHEAD)
    head_budget = int(usable * 2 / 3)
    tail_budget = usable - head_budget

    head = _fit_lines(lines, head_budget)
    # Fit tail from the end
    tail = list(reversed(_fit_lines(list(reversed(lines)), tail_budget)))

    # Avoid overlap
    tail_start_idx = len(lines) - len(tail)
    if tail_start_idx <= len(head):
        tail = []

    omitted = len(lines) - len(head) - len(tail)
    notice = _NOTICE_TEMPLATE.format(omitted=omitted, budget=budget)
    compressed = "\n".join(head) + notice + "\n".join(tail)
    return compressed


# ── Public API ────────────────────────────────────────────────────────────────

def apply(text: str, budget: int = 8000) -> str:
    """Run the full Phase 4 CRP pipeline on *text*.

    Order:
        1. Delta-only formatting (symbol substitution).
        2. Identifier mapping (path variable extraction).
        3. Token budget enforcement (hard truncation if needed).
    """
    text = apply_delta_format(text)
    text = apply_identifier_mapping(text)
    text = enforce_budget(text, budget)
    return text
