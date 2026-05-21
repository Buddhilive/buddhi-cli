"""
Server lifecycle manager: health-check and background auto-start for the
Buddhi FastAPI backend.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Optional

import httpx

DEFAULT_PORT = 58421
DEFAULT_HOST = "127.0.0.1"
STARTUP_TIMEOUT = 8.0   # seconds to wait for server to become ready
POLL_INTERVAL = 0.3


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
    Starts the FastAPI/uvicorn server in a daemon background thread.
    The thread is daemonized so it exits automatically when the TUI process
    terminates.
    """
    def _run() -> None:
        import uvicorn
        uvicorn.run(
            "server.main:app",
            host=host,
            port=port,
            log_level="error",   # suppress startup noise inside TUI
        )

    thread = threading.Thread(target=_run, daemon=True, name="buddhi-server")
    thread.start()


def ensure_server_ready(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    on_starting: Optional[Callable[[], None]] = None,
) -> bool:
    """
    High-level helper used by the TUI app on startup:
    1. If the server is already running → return True immediately.
    2. If not → start it in the background, then poll until ready or timeout.

    Args:
        on_starting: Optional callback invoked once when the server starts
                     being launched (e.g. to update a status label in the TUI).

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
