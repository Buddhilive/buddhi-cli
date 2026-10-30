"""Markdown relative link validator across skills and docs (skipping .archive/)."""

from __future__ import annotations

import os
import re
from pathlib import Path

_LINK_RE = re.compile(r"\[.*?\]\((?!https?://|mailto:)(.*?)\)")


def check_markdown_links(root: Path) -> list[dict[str, str]]:
    """Scan markdown files for broken relative links, skipping .archive directories."""
    broken: list[dict[str, str]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip .archive, .git, .venv, node_modules
        dirnames[:] = [
            d
            for d in dirnames
            if d not in (".archive", ".git", ".venv", "node_modules", "temp")
        ]

        for fname in filenames:
            if not fname.endswith(".md"):
                continue

            md_path = Path(dirpath) / fname
            try:
                content = md_path.read_text(encoding="utf-8")
            except OSError:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                for match in _LINK_RE.finditer(line):
                    raw_target = match.group(1).split("#")[0].strip()
                    if not raw_target:
                        continue

                    target_path = (md_path.parent / raw_target).resolve()
                    if not target_path.exists():
                        broken.append(
                            {
                                "source_file": str(md_path),
                                "line": str(idx),
                                "target": raw_target,
                            }
                        )

    return broken
