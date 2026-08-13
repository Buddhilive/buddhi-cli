"""Shared write-to-temp-then-replace helper for crash-safe artifact writes."""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        tmp_path.write_bytes(data)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))
