"""
Phase 2 — Domain-Specific Pattern Matching (State Machines).

Heuristically detects the domain of shell output and routes it through a
purpose-built abstractor that condenses it into a token-efficient summary.

Supported domains:
  - git      → `git status`, `git diff --stat`, `git log`, `git clone` …
  - linter   → TypeScript (tsc), ESLint, Ruff, Pylint, Rust (cargo), GCC/Clang …
  - traceback→ Python / Node.js exception tracebacks
  - generic  → No domain matched; returns text unchanged for Phase 3.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# Domain detection heuristics
# ═══════════════════════════════════════════════════════════════════════════

_GIT_SIGNATURES: list[re.Pattern[str]] = [
    re.compile(r"^(On branch|HEAD detached)", re.M),
    re.compile(r"^(Changes (not staged|to be committed)|Untracked files):$", re.M),
    re.compile(r"^diff --git a/", re.M),
    re.compile(r"^\[?(main|master|develop)\]? ", re.M),
    re.compile(r"^(Your branch|nothing to commit)", re.M),
]

_LINTER_SIGNATURES: list[re.Pattern[str]] = [
    # TypeScript / ESLint style: file.ts(10,5): error TS2322: …
    re.compile(r"\w+\.\w+\(\d+,\d+\):\s*(error|warning)\s+\w+\d+:"),
    # Ruff / Pylint: path/file.py:10:5: E501 …
    re.compile(r"[\w/\\.-]+\.py:\d+:\d+:\s+[A-Z]\d+"),
    # Rust compiler: error[E0123]:
    re.compile(r"error\[E\d{4}\]"),
    # GCC/Clang: file.c:10:5: error:
    re.compile(r"[\w/\\.-]+\.\w+:\d+:\d+:\s+(error|warning|note):"),
    # Generic: "N error(s)" or "N warning(s)"
    re.compile(r"\d+\s+(error|warning)s?\b", re.I),
]

_TRACEBACK_SIGNATURES: list[re.Pattern[str]] = [
    # Python
    re.compile(r"^Traceback \(most recent call last\):", re.M),
    re.compile(r"^\s+File \"[^\"]+\", line \d+", re.M),
    # Node.js
    re.compile(r"^Error:\s", re.M),
    re.compile(r"^\s+at\s+[\w.<>$]+\s+\(", re.M),
]


def _score(text: str, sigs: list[re.Pattern[str]]) -> int:
    return sum(1 for p in sigs if p.search(text))


def detect_domain(text: str) -> str:
    """Return the best-matching domain for *text*, or ``'generic'``."""
    scores = {
        "git": _score(text, _GIT_SIGNATURES),
        "linter": _score(text, _LINTER_SIGNATURES),
        "traceback": _score(text, _TRACEBACK_SIGNATURES),
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 1 else "generic"


# ═══════════════════════════════════════════════════════════════════════════
# Git Abstractor
# ═══════════════════════════════════════════════════════════════════════════

_GIT_STAGED_RE = re.compile(r"^\s+(modified|new file|deleted|renamed):\s+(.+)$", re.M)
_GIT_UNSTAGED_RE = re.compile(r"^\s+(modified|deleted):\s+(.+)$", re.M)
_GIT_UNTRACKED_RE = re.compile(r"^\t(\S.+)$", re.M)
_GIT_BRANCH_RE = re.compile(r"^On branch (.+)$", re.M)
_GIT_AHEAD_BEHIND_RE = re.compile(
    r"Your branch is (ahead|behind).+?by (\d+) commit", re.S
)
_GIT_NOTHING_RE = re.compile(r"nothing to commit", re.I)
_GIT_LOG_ENTRY_RE = re.compile(
    r"^commit ([0-9a-f]{7,40})\s*\nAuthor:\s*(.+)\s*\nDate:\s*(.+?)\n\s+(.+)$",
    re.M,
)
_GIT_DIFF_STAT_RE = re.compile(
    r"^\s*(.+?)\s+\|\s+(\d+)\s+([+\-]+)$", re.M
)
_GIT_CLONE_RE = re.compile(r"Cloning into '(.+?)'", re.I)


def abstract_git(text: str) -> str:
    """Condense `git` output into a compact summary line."""
    parts: list[str] = []

    branch_m = _GIT_BRANCH_RE.search(text)
    if branch_m:
        parts.append(f"branch:{branch_m.group(1).strip()}")

    ahead_m = _GIT_AHEAD_BEHIND_RE.search(text)
    if ahead_m:
        parts.append(f"{ahead_m.group(1)} by {ahead_m.group(2)}")

    if _GIT_NOTHING_RE.search(text):
        parts.append("clean working tree")
        return f"[Git: {', '.join(parts)}]"

    # Staged files
    staged = _GIT_STAGED_RE.findall(text)
    if staged:
        names = [s[1].strip() for s in staged]
        parts.append(f"{len(staged)} staged ({', '.join(names[:5])}{'…' if len(names) > 5 else ''})")

    # Unstaged files (below "Changes not staged" section)
    # Quick heuristic: count modified: lines not yet caught by staged
    unstaged_raw = re.findall(r"^\s+modified:\s+(.+)$", text, re.M)
    unstaged_names = [n.strip() for n in unstaged_raw if n.strip() not in [s[1].strip() for s in staged]]
    if unstaged_names:
        parts.append(f"{len(unstaged_names)} modified ({', '.join(unstaged_names[:5])}{'…' if len(unstaged_names) > 5 else ''})")

    # Untracked
    untracked = _GIT_UNTRACKED_RE.findall(text)
    if untracked:
        parts.append(f"{len(untracked)} untracked")

    # git log style
    log_entries = _GIT_LOG_ENTRY_RE.findall(text)
    if log_entries:
        summaries = [f"{sha[:7]} {msg[:60]}" for sha, _, _, msg in log_entries[:5]]
        parts.append("log: " + " | ".join(summaries))

    # git diff --stat style
    diff_entries = _GIT_DIFF_STAT_RE.findall(text)
    if diff_entries:
        total_changed = sum(int(n) for _, n, _ in diff_entries)
        parts.append(f"diff: {len(diff_entries)} files, {total_changed} changes")

    # git clone
    clone_m = _GIT_CLONE_RE.search(text)
    if clone_m:
        parts.append(f"cloned '{clone_m.group(1)}'")

    return f"[Git: {', '.join(parts) if parts else 'output condensed'}]"


# ═══════════════════════════════════════════════════════════════════════════
# Linter / Compiler Abstractor
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LintIssue:
    code: str
    filepath: str
    line: int
    message: str


# Unified pattern: captures (filepath, line, [col,] error_code, message)
_LINT_LINE_RE = re.compile(
    r"""
    ^(?P<file>[^\s:]+?)           # file path (no leading whitespace)
    [:(](?P<line>\d+)             # :line or (line
    (?:[,:(\s]\d+)?[):,]?\s*      # optional :col
    (?:error|warning|note|info)?\s*
    (?P<code>[A-Z]{0,5}\d{1,6})   # e.g. TS2322, E501, E0001, W123
    [\s:]+
    (?P<msg>.+)$
    """,
    re.VERBOSE | re.M,
)

# TypeScript-style: file.ts(10,5): error TS2322: ...
_TS_LINE_RE = re.compile(
    r"^(?P<file>[^\n]+?)\((?P<line>\d+),\d+\):\s*(?:error|warning)\s+"
    r"(?P<code>TS\d+):\s*(?P<msg>.+)$",
    re.M,
)

# Rust compiler errors: error[E0123]: ...  --> src/lib.rs:10:5
_RUST_ERROR_RE = re.compile(
    r"error\[(?P<code>E\d+)\]:\s*(?P<msg>[^\n]+)\n"
    r"\s*-->\s*(?P<file>[^\s:]+):(?P<line>\d+):",
    re.M,
)


def _parse_lint_issues(text: str) -> list[LintIssue]:
    issues: list[LintIssue] = []

    for m in _TS_LINE_RE.finditer(text):
        issues.append(LintIssue(m.group("code"), m.group("file"), int(m.group("line")), m.group("msg")))

    for m in _RUST_ERROR_RE.finditer(text):
        issues.append(LintIssue(m.group("code"), m.group("file"), int(m.group("line")), m.group("msg")))

    for m in _LINT_LINE_RE.finditer(text):
        # Skip duplicates already captured
        if not any(
            i.code == m.group("code") and i.filepath == m.group("file") and i.line == int(m.group("line"))
            for i in issues
        ):
            issues.append(LintIssue(m.group("code"), m.group("file"), int(m.group("line")), m.group("msg")))

    return issues


def abstract_linter(text: str) -> str:
    """Group linter/compiler errors by code and summarize."""
    issues = _parse_lint_issues(text)
    if not issues:
        # Fallback: extract the summary line (N errors, M warnings)
        summary_m = re.search(r"(\d+ errors?,?\s*\d* ?warnings?|\d+ warnings?)", text, re.I)
        return f"[Linter: {summary_m.group(0) if summary_m else 'output condensed'}]"

    by_code: dict[str, list[LintIssue]] = defaultdict(list)
    for issue in issues:
        by_code[issue.code].append(issue)

    lines: list[str] = []
    for code, group in sorted(by_code.items()):
        files = sorted({i.filepath for i in group})
        first = group[0]
        lines.append(
            f"[{code}: ×{len(group)} across {len(files)} file(s). "
            f"First: {first.filepath}:{first.line} — {first.message[:80]}]"
        )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Stack Trace Abstractor
# ═══════════════════════════════════════════════════════════════════════════

# Common paths that indicate external / library code
_EXTERNAL_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"site-packages[/\\]"),
    re.compile(r"node_modules[/\\]"),
    re.compile(r"dist-packages[/\\]"),
    re.compile(r"lib[/\\]python\d"),
    re.compile(r"<frozen importlib"),
    re.compile(r"<string>"),
]

_PY_FRAME_RE = re.compile(r'^\s+File "([^"]+)", line (\d+),')
_NODE_FRAME_RE = re.compile(r"^\s+at\s+[\w.<>$]+\s+\((.+):(\d+):\d+\)")


def _is_external_frame(filepath: str) -> bool:
    return any(p.search(filepath) for p in _EXTERNAL_PATH_PATTERNS)


def _abstract_python_traceback(lines: list[str]) -> str:
    """Preserve user-code frames; collapse external-library frames."""
    result: list[str] = []
    external_count = 0
    i = 0

    # Emit preamble until first "Traceback" line
    while i < len(lines) and "Traceback" not in lines[i]:
        result.append(lines[i])
        i += 1
    if i < len(lines):
        result.append(lines[i])
        i += 1

    while i < len(lines):
        line = lines[i]
        frame_m = _PY_FRAME_RE.match(line)
        if frame_m:
            filepath = frame_m.group(1)
            if _is_external_frame(filepath):
                external_count += 1
                i += 1
                # Skip the code snippet line that follows
                if i < len(lines) and not _PY_FRAME_RE.match(lines[i]):
                    i += 1
                continue
            else:
                if external_count:
                    result.append(
                        f"    ... [{external_count} frame(s) in external libraries hidden] ..."
                    )
                    external_count = 0
                result.append(line)
        else:
            if external_count and not lines[i].strip().startswith("File"):
                result.append(
                    f"    ... [{external_count} frame(s) in external libraries hidden] ..."
                )
                external_count = 0
            result.append(line)
        i += 1

    if external_count:
        result.append(
            f"    ... [{external_count} frame(s) in external libraries hidden] ..."
        )

    return "\n".join(result)


def abstract_traceback(text: str) -> str:
    """Condense a Python or Node.js stack trace."""
    lines = text.splitlines()

    # Python traceback
    if any("Traceback (most recent call last)" in l for l in lines):
        return _abstract_python_traceback(lines)

    # Node.js traceback — collapse external (node_modules) frames
    result: list[str] = []
    external_count = 0
    for line in lines:
        nm = _NODE_FRAME_RE.match(line)
        if nm:
            if _is_external_frame(nm.group(1)):
                external_count += 1
                continue
            if external_count:
                result.append(f"    ... [{external_count} frame(s) in node_modules hidden] ...")
                external_count = 0
        result.append(line)
    if external_count:
        result.append(f"    ... [{external_count} frame(s) in node_modules hidden] ...")
    return "\n".join(result)


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def apply(text: str) -> str:
    """Detect the domain of *text* and route it through the matching abstractor.

    Returns the condensed abstract, or the original text if no domain matched.
    """
    domain = detect_domain(text)
    if domain == "git":
        return abstract_git(text)
    elif domain == "linter":
        return abstract_linter(text)
    elif domain == "traceback":
        return abstract_traceback(text)
    # generic — pass through to Phase 3
    return text
