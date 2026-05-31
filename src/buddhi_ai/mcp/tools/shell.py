"""
buddhi_shell — subprocess execution engine.

Responsibilities:
- Detect and block interactive commands before launching.
- Run commands with a configurable timeout.
- Capture stdout + stderr combined.
- Surface timeout and blocking messages as structured error strings.
"""

import re
import subprocess
import sys
from typing import Optional

# Commands that require a live TTY or user input — cannot be non-interactive.
_INTERACTIVE_COMMANDS: frozenset[str] = frozenset(
    [
        "vim",
        "vi",
        "nano",
        "emacs",
        "pico",
        "less",
        "more",
        "top",
        "htop",
        "btop",
        "ssh",
        "telnet",
        "ftp",
        "sftp",
        "python",   # bare REPL
        "python3",
        "irb",
        "node",     # bare REPL
        "ipython",
        "mysql",    # interactive client
        "psql",
        "sqlite3",
        "redis-cli",
        "mongo",
    ]
)

# Flags that are safe overrides for normally-interactive programs
# (e.g. `python -c "..."`, `node -e "..."`)
_SAFE_OVERRIDE_FLAGS: frozenset[str] = frozenset(["-c", "-e", "--command", "-f", "--file"])


def _is_interactive(command: str) -> bool:
    """Return True if the command would open an interactive session."""
    parts = command.strip().split()
    if not parts:
        return False

    binary = parts[0].lower()
    # Strip common path prefixes
    binary = re.sub(r"^.*(\/|\\)", "", binary)
    # Strip Windows .exe suffix
    binary = re.sub(r"\.exe$", "", binary)

    if binary not in _INTERACTIVE_COMMANDS:
        return False

    # Allow if a safe non-interactive flag is present
    for flag in parts[1:]:
        if flag in _SAFE_OVERRIDE_FLAGS:
            return False

    return True


def run_command(
    command: str,
    timeout: int = 60,
    cwd: Optional[str] = None,
) -> tuple[str, int]:
    """Execute *command* in a subprocess and return ``(output, exit_code)``.

    The combined stdout + stderr stream is captured. If the process exceeds
    *timeout* seconds it is killed and an informative suffix is appended.

    Args:
        command: The shell command string to run.
        timeout: Wall-clock seconds before the process is forcefully terminated.
        cwd: Working directory override (defaults to current working directory).

    Returns:
        A 2-tuple of ``(output_text, exit_code)``.

    Raises:
        RuntimeError: If the command is detected as interactive.
    """
    if _is_interactive(command):
        raise RuntimeError(
            "[buddhi_shell: Blocked interactive command. Run non-interactively.]"
        )

    # On Windows, CREATE_NO_WINDOW prevents child processes spawned by cmd.exe
    # from inheriting the stdout PIPE handle, which can cause deadlocks when
    # the child keeps the handle open after the parent exits.
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        return result.stdout or "", result.returncode

    except subprocess.TimeoutExpired as exc:
        partial: str = ""
        if exc.stdout:
            if isinstance(exc.stdout, bytes):
                partial = exc.stdout.decode("utf-8", errors="replace")
            else:
                partial = exc.stdout
        return (
            partial + f"\n[buddhi_shell: Command timed out after {timeout}s]",
            -124,
        )
    except Exception as exc:  # noqa: BLE001
        return f"[buddhi_shell: Execution error — {exc}]", -1
