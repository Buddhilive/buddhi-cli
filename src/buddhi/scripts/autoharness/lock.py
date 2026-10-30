"""Cross-platform advisory file locking using msvcrt (Windows) and fcntl (POSIX)."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Platform-specific locking imports
_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import msvcrt
else:
    import fcntl  # type: ignore[import-not-found,unused-ignore]


@contextmanager
def file_lock(
    lock_path: Path, timeout_seconds: float = 10.0, retry_interval: float = 0.05
) -> Iterator[None]:
    """Acquires an exclusive advisory file lock across processes.

    Creates lock_path if it does not exist. Releases on block exit.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout_seconds

    # Open file descriptor
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o666)
    try:
        acquired = False
        while time.time() < deadline:
            try:
                if _IS_WINDOWS:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
                acquired = True
                break
            except OSError:
                time.sleep(retry_interval)

        if not acquired:
            raise TimeoutError(
                f"Could not acquire file lock on '{lock_path}' after {timeout_seconds}s"
            )

        yield

    finally:
        try:
            if _IS_WINDOWS:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)  # type: ignore[attr-defined]
                except OSError:
                    pass
        finally:
            os.close(fd)
