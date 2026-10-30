"""Path-scoped glob matching and safe recursive @path import expansion."""

from __future__ import annotations

import re
from pathlib import Path

import pathspec

from buddhi.memory.security import resolve_and_sandbox_import

_IMPORT_RE = re.compile(r"(?m)^(?P<indent>[ \t]*)@(?P<path>[^\s\r\n]+)")
MAX_IMPORT_DEPTH = 5
MAX_FILE_BYTES = 100_000
MAX_EXPANSION_BYTES = 256_000


def matches_active_files(patterns: list[str], active_files: list[str]) -> bool:
    """Returns True if patterns is empty (global) or matches any active file."""
    if not patterns:
        return True

    if not active_files:
        return False

    normalized_files = [f.replace("\\", "/").lstrip("/") for f in active_files]
    spec = pathspec.PathSpec.from_lines("gitignore", patterns)

    for f in normalized_files:
        if spec.match_file(f):
            return True

    return False


def resolve_imports(
    text: str,
    base_file: Path,
    workspace_root: Path,
    user_memory_root: Path,
    max_depth: int = MAX_IMPORT_DEPTH,
    visited: set[Path] | None = None,
    cumulative_bytes: list[int] | None = None,
) -> str:
    """Expands inline `@path/to/file` up to 5 hops with cycle & boundary checks."""
    if visited is None:
        visited = set()
    if cumulative_bytes is None:
        cumulative_bytes = [0]

    base_dir = base_file.parent if base_file.is_file() else base_file

    def _replace_import(match: re.Match) -> str:
        indent = match.group("indent")
        raw_target = match.group("path")

        try:
            target_path = resolve_and_sandbox_import(
                raw_ref=f"@{raw_target}",
                base_dir=base_dir,
                workspace_root=workspace_root,
                user_memory_root=user_memory_root,
            )
        except PermissionError as exc:
            return f"{indent}<!-- @import-forbidden-path: {exc} -->"
        except FileNotFoundError:
            return f"{indent}<!-- @import-missing-file: @{raw_target} -->"
        except (OSError, ValueError) as exc:
            return f"{indent}<!-- @import-error: {exc} -->"

        if target_path in visited:
            return f"{indent}<!-- @import-cycle-detected: @{raw_target} -->"

        if len(visited) >= max_depth:
            return f"{indent}<!-- @import-depth-exceeded: max {max_depth} hops -->"

        file_size = target_path.stat().st_size
        if file_size > MAX_FILE_BYTES:
            return f"{indent}<!-- @import-file-too-large: {file_size} bytes exceeds {MAX_FILE_BYTES} max -->"

        cumulative_bytes[0] += file_size
        if cumulative_bytes[0] > MAX_EXPANSION_BYTES:
            return f"{indent}<!-- @import-budget-exceeded: {cumulative_bytes[0]} bytes exceeds {MAX_EXPANSION_BYTES} max -->"

        sub_visited = set(visited)
        sub_visited.add(target_path)

        child_content = target_path.read_text(encoding="utf-8")
        child_expanded = resolve_imports(
            text=child_content,
            base_file=target_path,
            workspace_root=workspace_root,
            user_memory_root=user_memory_root,
            max_depth=max_depth,
            visited=sub_visited,
            cumulative_bytes=cumulative_bytes,
        )

        indented_lines = [
            f"{indent}{line}" if line.strip() else line
            for line in child_expanded.splitlines()
        ]
        return "\n".join(indented_lines)

    return _IMPORT_RE.sub(_replace_import, text)
