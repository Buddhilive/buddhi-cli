"""Atomic file writing utilities using mkstemp and os.replace."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(target_path: Path, data: bytes) -> None:
    """Atomically write binary data to target_path, preserving existing mode if present."""
    target_path = target_path.resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    mode = 0o644
    if target_path.exists():
        try:
            mode = target_path.stat().st_mode & 0o777
        except OSError:
            pass

    fd, temp_file = tempfile.mkstemp(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        try:
            os.chmod(temp_file, mode)
        except OSError:
            pass

        os.replace(temp_file, str(target_path))
    except Exception:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except OSError:
            pass
        raise


def atomic_write_text(target_path: Path, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text content to target_path."""
    atomic_write_bytes(target_path, content.encode(encoding))

