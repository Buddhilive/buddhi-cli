"""Size budget and pre-commit ratchet for git-tracked source files.

Ported from check-file-size.mjs in @dzhng/skills (MIT License).
Ensures source files stay small enough for an AI agent to read whole (~8,000 tokens).
Tokens are estimated as bytes // 4.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

PRAGMA = "@ratchet-files-ignore"
PRAGMA_LINES = 10

CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".cs",
    ".csx",
    ".go",
    ".java",
    ".kt",
    ".kts",
    ".scala",
    ".clj",
    ".cljs",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".py",
    ".pyw",
    ".pyi",
    ".rb",
    ".rake",
    ".rs",
    ".swift",
    ".php",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".lua",
    ".zig",
    ".pl",
    ".pm",
    ".r",
    ".dart",
    ".v",
    ".sv",
    ".proto",
    ".sql",
    ".ex",
    ".exs",
    ".erl",
    ".hrl",
}

PROSE_EXTENSIONS = {
    ".md",
    ".markdown",
    ".mdown",
    ".txt",
    ".rst",
    ".adoc",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
}


@dataclass
class FileViolation:
    path: str
    bytes: int
    before: int | None

    @property
    def tokens(self) -> int:
        return round(self.bytes / 4)

    @property
    def before_tokens(self) -> int | None:
        return round(self.before / 4) if self.before is not None else None


def is_source_file(path_str: str) -> bool:
    ext = os.path.splitext(path_str)[1].lower()
    if not ext:
        return False
    return ext in CODE_EXTENSIONS and ext not in PROSE_EXTENSIONS


def run_git(args: list[str], input_bytes: bytes | None = None) -> str:
    """Execute git with pipe stdio and utf-8 decoding."""
    result = subprocess.run(
        ["git", *args],
        input=input_bytes,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def get_git_root() -> Path:
    """Return git repo toplevel directory."""
    out = run_git(["rev-parse", "--show-toplevel"]).strip()
    return Path(out).resolve()


def get_unauthored(paths: list[str]) -> set[str]:
    """Return paths marked linguist-generated or linguist-vendored in git index."""
    if not paths:
        return set()
    input_data = "\0".join(paths).encode("utf-8")
    try:
        proc = subprocess.run(
            [
                "git",
                "check-attr",
                "--cached",
                "-z",
                "--stdin",
                "linguist-generated",
                "linguist-vendored",
            ],
            input=input_data,
            capture_output=True,
            check=True,
        )
        parts = proc.stdout.decode("utf-8", errors="replace").split("\0")
        marked = set()
        for i in range(0, len(parts) - 2, 3):
            attr_val = parts[i + 2]
            if attr_val in ("true", "set"):
                marked.add(parts[i])
        return marked
    except (subprocess.CalledProcessError, OSError):
        return set()


def blob_bytes(spec: str) -> int | None:
    """Return byte size of a git blob spec (e.g. ':path' or 'HEAD:path')."""
    try:
        out = run_git(["cat-file", "-s", spec]).strip()
        return int(out)
    except (subprocess.CalledProcessError, OSError, ValueError):
        return None


def is_ignored(spec: str) -> bool:
    """Check if the first PRAGMA_LINES contain @ratchet-files-ignore."""
    try:
        proc = subprocess.run(
            ["git", "cat-file", "blob", spec],
            capture_output=True,
            check=True,
        )
        lines = proc.stdout.decode("utf-8", errors="replace").splitlines()
        first_lines = lines[:PRAGMA_LINES]
        return any(PRAGMA in line for line in first_lines)
    except (subprocess.CalledProcessError, OSError):
        return False


def format_tokens(num_bytes: int) -> str:
    toks = round(num_bytes / 4)
    return f"~{toks:,} tokens"


def check_all_files(max_tokens: int = 8000) -> tuple[int, list[str]]:
    """Scan all tracked files in git index.

    Returns (exit_code, output_lines).
    """
    max_bytes = max_tokens * 4
    try:
        raw_files = run_git(["ls-files", "-z"]).split("\0")
    except (subprocess.CalledProcessError, OSError) as exc:
        return 2, [f"error: failed running git ls-files: {exc}"]

    files = [f for f in raw_files if f.strip() and is_source_file(f)]
    unauthored_files = get_unauthored(files)
    candidates = [f for f in files if f not in unauthored_files]

    violations: list[tuple[str, int]] = []
    opted_out = 0

    for path in candidates:
        size = blob_bytes(f":{path}")
        if size is not None and size > max_bytes:
            if is_ignored(f":{path}"):
                opted_out += 1
            else:
                violations.append((path, size))

    violations.sort(key=lambda item: item[1], reverse=True)

    lines: list[str] = []
    for path, size in violations:
        tok_str = format_tokens(size).rjust(15)
        lines.append(f"{tok_str}  {path}")

    lines.append(f"Source files over {max_tokens:,} tokens: {len(violations)}.")
    if opted_out > 0:
        lines.append(f"Over the budget but opted out with {PRAGMA}: {opted_out}.")

    exit_code = 1 if violations else 0
    return exit_code, lines


def check_staged_files(
    paths: list[str], max_tokens: int = 8000
) -> tuple[int, list[str]]:
    """Verify staged versions of paths against ratchet."""
    max_bytes = max_tokens * 4
    try:
        root = get_git_root()
    except (subprocess.CalledProcessError, OSError) as exc:
        return 2, [f"error: not a git repository: {exc}"]

    # Get renames from index
    renames: dict[str, str] = {}
    try:
        diff_out = run_git(["diff", "--cached", "--find-renames", "--name-status"])
        for line in diff_out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].startswith("R"):
                renames[parts[2]] = parts[1]
    except (subprocess.CalledProcessError, OSError):
        pass

    normalized: list[str] = []
    for p in paths:
        try:
            rel = os.path.relpath(os.path.realpath(p), root)
        except (ValueError, OSError):
            rel = os.path.relpath(p, root)
        rel_posix = rel.replace("\\", "/")
        if is_source_file(rel_posix):
            normalized.append(rel_posix)

    unauthored = get_unauthored(normalized)
    eval_paths = [p for p in normalized if p not in unauthored]

    failures: list[FileViolation] = []
    for p in eval_paths:
        size = blob_bytes(f":{p}")
        if size is None or size <= max_bytes or is_ignored(f":{p}"):
            continue
        orig = renames.get(p, p)
        before = blob_bytes(f"HEAD:{orig}")
        if before is not None and size <= before:
            continue
        failures.append(FileViolation(path=p, bytes=size, before=before))

    if not failures:
        return 0, []

    lines = [
        f"Commit refused: source files over the budget of {format_tokens(max_bytes)} (bytes // 4)."
    ]
    for f in failures:
        frozen = f.before is not None and f.before > max_bytes
        limit: int = f.before if (frozen and f.before is not None) else max_bytes
        if frozen and f.before is not None:
            why = (
                f"already over budget at {format_tokens(f.before)}, so it may not grow"
            )
        elif f.before is None:
            why = "a new file, so it must fit the budget"
        else:
            why = f"was {format_tokens(f.before)}, so it must fit the budget"
        lines.append(f"  {f.path}: {format_tokens(f.bytes)}, {why}.")
        lines.append(f"    Cut at least {f.bytes - limit:,} bytes.")

    return 1, lines


def selftest() -> tuple[int, str]:
    """Run internal sanity checks."""
    assert is_source_file("foo.py")
    assert is_source_file("bar.ts")
    assert not is_source_file("README.md")
    assert not is_source_file("data.json")
    assert format_tokens(4000) == "~1,000 tokens"
    return 0, "selftest: check-file-size OK"
