"""
shell_proxy — Terminal Execution Shield for Antigravity PreToolUse hooks.

Intercepts ``run_command`` tool calls, executes the command through a
sandboxed subprocess (supporting both PowerShell on Windows and sh/bash on
POSIX), compresses the output using the buddhi_shell 4-phase pipeline, and
returns the compressed result inside a DENY payload so the raw terminal
output never touches the LLM prompt history.

Protocol:
  1. Read JSON from stdin (Antigravity hook payload).
  2. Extract CommandLine, Cwd from toolCall.args.
  3. Execute via subprocess with platform-aware shell selection.
  4. Run the 4-phase compression pipeline on stdout+stderr.
  5. Emit a deny decision on stdout containing the compressed result.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Optional


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def _detect_shell() -> tuple[str, bool]:
    """Return (shell_executable, use_shell_flag) for the current platform.

    On Windows, prefers PowerShell (pwsh or powershell.exe).
    On POSIX, uses /bin/sh.
    """
    if sys.platform == "win32":
        # Prefer pwsh (PowerShell 7+) then fall back to Windows PowerShell
        for candidate in ("pwsh", "powershell"):
            try:
                subprocess.run(
                    [candidate, "-Version"],
                    capture_output=True,
                    timeout=5,
                )
                return candidate, False  # shell=False, we call the binary directly
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        # Final fallback: cmd.exe via shell=True
        return "cmd.exe", True
    return "/bin/sh", True


def _run_sandboxed(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 120,
) -> tuple[str, int]:
    """Execute *command* in a sandboxed subprocess.

    Returns (combined_output, exit_code).
    """
    shell_bin, use_shell = _detect_shell()
    resolved_cwd = cwd or os.getcwd()

    try:
        if use_shell:
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                cwd=resolved_cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        else:
            # PowerShell direct invocation
            result = subprocess.run(
                [shell_bin, "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                cwd=resolved_cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        return result.stdout or "", result.returncode

    except subprocess.TimeoutExpired as exc:
        partial = ""
        if exc.stdout:
            partial = (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout
            )
        return partial + f"\n[buddhi_shell: Timed out after {timeout}s]", -1

    except Exception as exc:
        return f"[buddhi_shell: Execution error — {exc}]", -1


def _compress(raw_output: str, budget: int = 8000) -> str:
    """Run the buddhi 4-phase compression pipeline on raw shell output."""
    try:
        from buddhi_ai.mcp.compression.pipeline import process

        return process(raw_output, budget=budget)
    except ImportError:
        # Fallback: basic ANSI strip + truncation if compression is unavailable
        cleaned = _strip_ansi(raw_output)
        if budget > 0 and len(cleaned) > budget:
            return cleaned[:budget] + "\n[...truncated]"
        return cleaned


def main() -> None:
    """Entrypoint for the shell_proxy hook script."""
    raw = sys.stdin.read()
    if not raw.strip():
        json.dump({"decision": "allow"}, sys.stdout)
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        json.dump({"decision": "allow"}, sys.stdout)
        return

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")

    if tool_name != "run_command":
        json.dump({"decision": "allow"}, sys.stdout)
        return

    args = tool_call.get("args", {})
    command_line = args.get("CommandLine", "")
    cwd = args.get("Cwd")
    timeout = args.get("WaitMsBeforeAsync", 120000) // 1000  # Convert ms → s
    timeout = min(max(timeout, 5), 300)  # Clamp to 5-300s

    if not command_line:
        json.dump(
            {"decision": "deny", "reason": "[buddhi_shell: Empty command line]"},
            sys.stdout,
        )
        return

    # Execute and compress
    raw_output, exit_code = _run_sandboxed(command_line, cwd=cwd, timeout=timeout)
    header = f"[exit:{exit_code}] $ {command_line}"
    compressed = _compress(raw_output)

    json.dump(
        {
            "decision": "deny",
            "reason": (
                f"Command executed via buddhi_shell pipeline.\n\n"
                f"{header}\n{compressed}"
            ),
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
