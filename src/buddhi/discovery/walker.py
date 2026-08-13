"""Filesystem walking: language detection, exclude rules, size guard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pathspec

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".buddhi",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "target",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".idea",
    ".vscode",
    "bin",
    "obj",
}


@dataclass
class DiscoveredFile:
    abs_path: Path
    rel_path: str  # posix-style, relative to scan root
    language: str


@dataclass
class WalkResult:
    files: list[DiscoveredFile]
    directories: set[str]  # posix-relative dirs containing at least one included file
    skipped_too_large: list[str]
    skipped_unsupported_grammar: dict[str, int]  # language -> count


def _load_gitignore_spec(root: Path) -> pathspec.PathSpec | None:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.is_file():
        return None
    try:
        lines = gitignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return pathspec.PathSpec.from_lines("gitignore", lines)


def walk(
    root: Path,
    *,
    max_file_size: int = 2_000_000,
    available_languages: set[str] | None = None,
) -> WalkResult:
    """Walk `root`, returning files whose extension maps to a known language.

    `available_languages` restricts which detected languages are actually
    included (grammars that failed to load are counted, not walked into
    the parse stage).
    """
    gitignore_spec = _load_gitignore_spec(root)
    files: list[DiscoveredFile] = []
    directories: set[str] = set()
    skipped_too_large: list[str] = []
    skipped_unsupported_grammar: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDED_DIRS]
        current_dir = Path(dirpath)

        if gitignore_spec is not None:
            pruned = []
            for d in dirnames:
                rel = (current_dir / d).relative_to(root).as_posix()
                if gitignore_spec.match_file(rel + "/"):
                    continue
                pruned.append(d)
            dirnames[:] = pruned

        for filename in sorted(filenames):
            abs_path = current_dir / filename
            rel_path = abs_path.relative_to(root).as_posix()

            if gitignore_spec is not None and gitignore_spec.match_file(rel_path):
                continue

            ext = abs_path.suffix.lower()
            language = EXTENSION_TO_LANGUAGE.get(ext)
            if language is None:
                continue

            if available_languages is not None and language not in available_languages:
                skipped_unsupported_grammar[language] = (
                    skipped_unsupported_grammar.get(language, 0) + 1
                )
                continue

            try:
                size = abs_path.stat().st_size
            except OSError:
                continue
            if size > max_file_size:
                skipped_too_large.append(rel_path)
                continue

            files.append(DiscoveredFile(abs_path=abs_path, rel_path=rel_path, language=language))
            parent = Path(rel_path).parent.as_posix()
            while parent and parent != ".":
                directories.add(parent)
                parent = Path(parent).parent.as_posix()

    files.sort(key=lambda f: f.rel_path)
    return WalkResult(
        files=files,
        directories=directories,
        skipped_too_large=skipped_too_large,
        skipped_unsupported_grammar=skipped_unsupported_grammar,
    )
