"""Antigravity PreToolUse hook adapter logic for RTK.

Extracts command lines from tool invocation payloads, evaluates rewrite rules,
and returns Antigravity overwrite structures. Fail-open everywhere.
"""

from __future__ import annotations

import logging
from typing import Any

from buddhi.scripts.rtk.rewrite import evaluate_rewrite

logger = logging.getLogger(__name__)


def extract_command_from_payload(payload: Any) -> tuple[str | None, str | None]:
    """Extract command string and key path from Antigravity tool payload.

    Returns:
        (command_str, field_key) or (None, None)
    """
    if not isinstance(payload, dict):
        return None, None

    # Pattern 1: {"toolCall": {"name": "run_command", "args": {"CommandLine": "..."}}}
    tool_call = payload.get("toolCall") or payload.get("tool_call")
    if isinstance(tool_call, dict):
        tool_name = tool_call.get("name", "")
        if tool_name in ("run_command", "terminal", "bash", "execute_command"):
            args = tool_call.get("args") or tool_call.get("parameters") or {}
            if isinstance(args, dict):
                for key in ("CommandLine", "command", "cmd"):
                    if key in args and isinstance(args[key], str):
                        return args[key], f"toolCall.args.{key}"

    # Pattern 2: {"command": "..."} or {"CommandLine": "..."}
    for key in ("CommandLine", "command", "cmd"):
        val = payload.get(key)
        if isinstance(val, str):
            return val, key

    # Pattern 3: Nested input/parameters
    for outer in ("input", "tool_input", "parameters"):
        inner = payload.get(outer)
        if isinstance(inner, dict):
            for key in ("CommandLine", "command", "cmd"):
                val = inner.get(key)
                if isinstance(val, str):
                    return val, f"{outer}.{key}"

    return None, None


def handle_hook_payload(payload: Any) -> dict[str, Any]:
    """Process an Antigravity PreToolUse hook payload and return overwrite or empty dict."""
    try:
        command, field_path = extract_command_from_payload(payload)
        if not command:
            return {}

        decision = evaluate_rewrite(command)
        if decision.action != "rewrite":
            return {}

        # Construct Antigravity overwrite structure
        # If field was CommandLine inside toolCall.args
        if field_path == "toolCall.args.CommandLine":
            return {"overwrite": {"CommandLine": decision.rewritten_command}}
        elif field_path == "toolCall.args.command":
            return {"overwrite": {"command": decision.rewritten_command}}
        else:
            return {
                "overwrite": {
                    "CommandLine": decision.rewritten_command,
                    "command": decision.rewritten_command,
                }
            }

    except Exception as err:  # noqa: BLE001
        logger.warning("Error in RTK hook handler: %s", err)
        return {}
