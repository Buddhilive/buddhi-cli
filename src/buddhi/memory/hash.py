"""Deterministic provenance hashing, line-slicing, and staleness detection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from buddhi.memory.models import MemorySource
from buddhi.memory.security import parse_source_resource


@dataclass
class StalenessResult:
    is_stale: bool
    reason: str | None = (
        None  # "hash_mismatch" | "file_not_found" | "invalid_line_range"
    )
    expected_hash: str = ""
    current_hash: str = ""


def compute_content_hash(workspace_root: Path, resource: str) -> str:
    """Computes SHA-256 of full file or line slice #Lstart-Lend with normalized LF line endings."""
    file_path, start_line, end_line = parse_source_resource(resource, workspace_root)
    if not file_path.is_file():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    # Normalize CRLF -> LF for cross-platform hash parity
    normalized = raw_text.replace("\r\n", "\n")

    if start_line is not None and end_line is not None:
        lines = normalized.splitlines(keepends=True)
        # 1-indexed line numbers
        selected = lines[start_line - 1 : end_line]
        slice_text = "".join(selected)
    else:
        slice_text = normalized

    return hashlib.sha256(slice_text.encode("utf-8")).hexdigest()


def verify_source_staleness(
    workspace_root: Path, source: MemorySource
) -> StalenessResult:
    """Checks whether the on-disk code snippet still matches source.content_hash."""
    try:
        current_hash = compute_content_hash(workspace_root, source.resource)
    except FileNotFoundError:
        return StalenessResult(
            is_stale=True,
            reason="file_not_found",
            expected_hash=source.content_hash,
            current_hash="",
        )
    except ValueError as exc:
        return StalenessResult(
            is_stale=True,
            reason=f"invalid_resource: {exc}",
            expected_hash=source.content_hash,
            current_hash="",
        )

    if current_hash != source.content_hash:
        return StalenessResult(
            is_stale=True,
            reason="hash_mismatch",
            expected_hash=source.content_hash,
            current_hash=current_hash,
        )

    return StalenessResult(
        is_stale=False,
        reason=None,
        expected_hash=source.content_hash,
        current_hash=current_hash,
    )
