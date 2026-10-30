"""Safe slugging, Windows MAX_PATH budgeting, collision deduplication, and atomic writes.

Adapted from graphify's wiki and path utilities to ensure cross-platform safety
on Windows (NTFS), macOS (APFS), and Linux.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

# Characters forbidden in slugs because the link target and disk filename
# must be identical CommonMark link targets without percent-encoding:
# < > : " / \ | ? *   Windows-reserved in filenames
# ( )                 parentheses delimit link destinations in Markdown
# #                   starts a fragment
# %                   starts percent-escape
# control chars       illegal in filenames and links
_UNSAFE_SLUG_CHARS = re.compile(r'[<>:"/\\|?*#%\x00-\x1f\x7f]')
_SLUG_SUFFIX_RESERVE = 5
_WINDOWS_MAX_PATH = 260


def stem_filename_budget(
    output_dir: Path, reserve: int = _SLUG_SUFFIX_RESERVE, limit: int = 200
) -> int:
    """Calculate the maximum characters allowed for a filename stem in output_dir.

    On Windows, path lengths are capped at MAX_PATH (260 chars) unless long paths
    are explicitly enabled. This caps the slug so that:
    len(output_dir) + 1 (separator) + stem + reserve + 3 (.md) < 260.
    """
    if sys.platform != "win32":
        return limit

    try:
        resolved_len = len(str(output_dir.resolve()))
    except (OSError, RuntimeError):
        resolved_len = len(str(output_dir))

    # Available budget: 259 (max index) - dir - 1 (sep) - 3 (.md) - reserve
    budget = _WINDOWS_MAX_PATH - 1 - resolved_len - 1 - 3 - reserve
    if budget < 10:
        return 10
    return min(limit, budget)


def safe_filename(name: str, limit: int = 200) -> str:
    """Sanitize label into a safe filename and verbatim Markdown link destination.

    Substitutes Windows-reserved characters with underscores, collapses whitespace,
    and drops parentheses to keep dunder methods (__init__) and callables readable.
    """
    s = name.replace("/", "-").replace("\\", "-").replace(":", "-").replace(" ", "_")
    s = s.replace("(", "").replace(")", "")
    s = _UNSAFE_SLUG_CHARS.sub("_", s)
    s = s.strip(". ")
    return s[:limit] if s else "unnamed"


class SlugResolver:
    """Two-pass unique slug assigner with case-insensitive collision handling."""

    def __init__(self, limit: int = 200) -> None:
        self.limit = limit
        self.used_slugs_lower: set[str] = {"index"}
        self.label_to_slug: dict[str, str] = {}

    def register(self, label: str) -> str:
        """Register a label and assign it a unique case-deduplicated slug."""
        if label in self.label_to_slug:
            return self.label_to_slug[label]

        base = safe_filename(label, self.limit)
        slug = base
        n = 2
        while slug.lower() in self.used_slugs_lower:
            slug = f"{base}_{n}"
            n += 1

        self.used_slugs_lower.add(slug.lower())
        self.label_to_slug[label] = slug
        return slug

    def get(self, label: str, default: str | None = None) -> str | None:
        """Get the registered slug for a label."""
        return self.label_to_slug.get(label, default)


def write_text_atomic_if_changed(
    path: Path, content: str, encoding: str = "utf-8"
) -> bool:
    """Write text atomically only if content has changed.

    Returns True if the file was written, False if bytes were identical.
    This prevents modifying file mtime on unchanged content, which avoids
    triggering infinite Pelican file-watcher rebuild loops.
    """
    path = Path(path)
    if path.is_file():
        try:
            existing = path.read_text(encoding=encoding)
            if existing == content:
                return False
        except OSError:
            pass

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = path.parent
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=temp_dir, delete=False, encoding=encoding
        ) as tf:
            tf.write(content)
            temp_path = Path(tf.name)
        os.replace(temp_path, path)
    except OSError:
        # Fallback if atomic replace fails
        path.write_text(content, encoding=encoding)
    return True
