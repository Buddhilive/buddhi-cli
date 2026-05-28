"""
Antigravity hook installation utilities for `buddhi setup`.

Responsibilities:
  1. Write the enforcer script to ~/.buddhi/hooks/enforcer.py
  2. Merge BeforeTool entries into ~/.gemini/settings.json (idempotent)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Native tool names intercepted by the enforcer.
_INTERCEPTED_TOOLS: list[str] = ["run_command", "grep_search", "view_file"]

# Sentinel written into settings.json to detect existing buddhi hooks.
_MARKER = "buddhi-hook-enforcer"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_enforcer_script(hooks_dir: Path) -> Path:
    """Copy the bundled enforcer template to *hooks_dir/enforcer.py*.

    Creates the directory if it does not exist. Returns the installed path.
    On POSIX systems the file is made executable.
    """
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Locate the template shipped alongside this module.
    template_path = Path(__file__).parent / "enforcer.py"
    dest = hooks_dir / "enforcer.py"

    shutil.copy2(template_path, dest)

    # Make executable on POSIX so it can be called directly if needed.
    if sys.platform != "win32":
        current = dest.stat().st_mode
        dest.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return dest


def install_antigravity_hooks(enforcer_path: Path) -> None:
    """Merge buddhi BeforeTool hook entries into ~/.gemini/settings.json.

    The merge is **idempotent**: if the sentinel marker is already present the
    function prints a notice and returns without modifying the file.
    """
    settings_path = Path.home() / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine the Python interpreter command.
    python_cmd = _resolve_python_cmd()
    # Normalise path separators for the platform (Windows needs forward-slashes
    # in JSON strings too, but Python's as_posix is safer cross-platform).
    enforcer_str = enforcer_path.as_posix()
    hook_command = f"{python_cmd} {enforcer_str}"

    # Build BeforeTool entries — one matcher per intercepted tool.
    new_before_tool_entries = [
        {
            "matcher": f"^({tool})$",
            "hooks": [{"type": "command", "command": hook_command}],
            # Sentinel so we can detect existing installation on re-runs.
            "__buddhi": _MARKER,
        }
        for tool in _INTERCEPTED_TOOLS
    ]

    # Load existing settings (handle missing file and JSONC comments).
    if settings_path.exists():
        try:
            raw = settings_path.read_text(encoding="utf-8")
            clean = re.sub(r"//[^\n]*", "", raw)  # strip // comments
            existing: dict = json.loads(clean) if clean.strip() else {}
        except Exception as exc:
            print(
                f"[buddhi hooks] Warning: could not parse {settings_path}: {exc}. "
                "Reinitialising with a fresh hooks config."
            )
            existing = {}
    else:
        existing = {}

    # Check for sentinel — bail early if already installed.
    hooks_section: dict = existing.get("hooks", {})
    before_tool: list = hooks_section.get("BeforeTool", [])
    if any(entry.get("__buddhi") == _MARKER for entry in before_tool):
        print(
            f"[buddhi hooks] BeforeTool hooks already installed in {settings_path}. "
            "Skipping (run 'buddhi setup' again to re-install after removing the old entries)."
        )
        return

    # Merge: append buddhi entries to any existing BeforeTool list.
    hooks_section["BeforeTool"] = before_tool + new_before_tool_entries
    existing["hooks"] = hooks_section

    try:
        settings_path.write_text(
            json.dumps(existing, indent=4), encoding="utf-8"
        )
        print(f"[buddhi hooks] Installed BeforeTool hooks at {settings_path}")
        print(
            f"[buddhi hooks] Enforcer script: {enforcer_path}\n"
            f"[buddhi hooks] Intercepting: {', '.join(_INTERCEPTED_TOOLS)}"
        )
    except Exception as exc:
        print(f"[buddhi hooks] Error writing {settings_path}: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_python_cmd() -> str:
    """Return a best-effort Python interpreter command.

    Prefers the currently running interpreter (absolute path) so the hook
    works even when Python is not on PATH in the IDE shell.
    """
    interpreter = sys.executable
    if interpreter and os.path.isabs(interpreter):
        return interpreter
    # Fallback: prefer python3 on POSIX, python on Windows.
    return "python" if sys.platform == "win32" else "python3"
