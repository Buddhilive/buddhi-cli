"""
Server lifecycle manager: health-check and background auto-start for the
Buddhi FastAPI backend.
"""
from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

import httpx

DEFAULT_PORT = 58421
DEFAULT_HOST = "127.0.0.1"
STARTUP_TIMEOUT = 30.0  # seconds to wait for server to become ready
POLL_INTERVAL = 0.3

# Log file — all server stdout/stderr lands here, never in the TUI terminal
_LOG_DIR = Path.home() / ".buddhi"
_SERVER_LOG = _LOG_DIR / "server.log"

# Module-level reference so we can check the process is still alive
_server_proc: Optional[subprocess.Popen] = None


def is_server_running(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Synchronous health check — returns True if /health responds 200."""
    try:
        resp = httpx.get(f"http://{host}:{port}/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def start_server_background(
    host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> None:
    """
    Starts the FastAPI/uvicorn server as a child *subprocess* so its
    stdout and stderr are completely isolated from the TUI's terminal.

    All server output is appended to ~/.buddhi/server.log.
    The process is not daemonized at the OS level, but we store a reference
    so the TUI can leave it running after exit (it will be orphaned and keep
    serving) or kill it if needed.
    """
    global _server_proc

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_fh = open(_SERVER_LOG, "a", buffering=1)

    # Re-use the same Python interpreter that is running the TUI so we stay
    # inside the same venv / uv environment.
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "server.main:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "warning",
        "--no-access-log",
    ]

    _server_proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=log_fh,
        stdin=subprocess.DEVNULL,
        # Keep the child alive even after the parent exits
        # (on Windows this is the default; on Unix we avoid setsid so we can
        # still kill it, but we don't set close_fds=False either)
    )


def ensure_server_ready(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    on_starting: Optional[Callable[[], None]] = None,
) -> bool:
    """
    High-level helper used by the TUI app on startup:
    1. If the server is already running → return True immediately.
    2. If not → start it as a subprocess, then poll until ready or timeout.

    Args:
        on_starting: Optional callback invoked once when the server is being
                     launched (e.g. to update a status label in the TUI).

    Returns:
        True if the server is ready within STARTUP_TIMEOUT, False otherwise.
    """
    if is_server_running(host, port):
        return True

    if on_starting:
        on_starting()

    start_server_background(host, port)

    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL)
        if is_server_running(host, port):
            return True

    return False
