"""SHA-256 AST extraction cache and git commit resolution."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def compute_sha256(data: bytes) -> str:
    """Compute the hexadecimal SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def get_git_head_sha(root: Path) -> str | None:
    """Return the current git HEAD commit SHA, or None if unavailable.

    Tries reading .git/HEAD directly first for zero-subprocess speed,
    falling back to git rev-parse HEAD.
    """
    git_dir = root / ".git"
    if git_dir.is_dir():
        head_file = git_dir / "HEAD"
        if head_file.is_file():
            try:
                head_content = head_file.read_text(encoding="utf-8").strip()
                if not head_content.startswith("ref:"):
                    if len(head_content) == 40 and all(
                        c in "0123456789abcdefABCDEF" for c in head_content
                    ):
                        return head_content
                else:
                    ref_rel = head_content[4:].strip()
                    ref_file = git_dir / ref_rel
                    if ref_file.is_file():
                        sha = ref_file.read_text(encoding="utf-8").strip()
                        if len(sha) == 40:
                            return sha
                    packed_refs = git_dir / "packed-refs"
                    if packed_refs.is_file():
                        for line in packed_refs.read_text(
                            encoding="utf-8", errors="replace"
                        ).splitlines():
                            line = line.strip()
                            if line.startswith(("#", "^")) or not line:
                                continue
                            parts = line.split()
                            if len(parts) == 2 and parts[1] == ref_rel:
                                return parts[0]
            except OSError:
                pass

    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=1.5,
        )
        if res.returncode == 0:
            sha = res.stdout.strip()
            if len(sha) == 40:
                return sha
    except (OSError, subprocess.SubprocessError):
        pass

    return None


def serialize_extraction_payload(payload: dict[str, Any]) -> str:
    """Serialize extraction payload to JSON string."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def deserialize_extraction_payload(payload_json: str) -> dict[str, Any]:
    """Safely deserialize extraction payload from JSON string."""
    return json.loads(payload_json)
