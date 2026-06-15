#!/usr/bin/env python3
"""
Buddhi hook enforcer — installed globally by `buddhi setup`.

Antigravity calls this script via a BeforeTool hook whenever the LLM attempts
to use a native tool that has a buddhi_* MCP replacement. The script reads the
JSON tool-call payload from stdin and writes a decision to stdout:
  - "deny" (with a corrective message) for intercepted native tools.
  - "allow" for everything else.

Protocol reference: https://antigravity.google/docs/hooks
"""
import sys
import json

# Maps each intercepted native tool → (replacement MCP tool, parameter hint)
ENFORCEMENT_MAP: dict[str, tuple[str, str]] = {
    "run_command": (
        "buddhi_run_command",
        "Pass 'command' (str) and optional 'timeout_seconds' (int).",
    ),
    "grep_search": (
        "buddhi_grep_search",
        "Pass 'query' (str) and optional 'globs' (list[str]).",
    ),
    "view_file": (
        "buddhi_view_file",
        "Pass 'path' (str), 'task' (str), and optional 'mode' (str).",
    ),
}


def _deny_response(tool_name: str, correct_tool: str, hint: str) -> str:
    """Build a BeforeTool deny JSON response."""
    message = (
        f"[Buddhi] The native tool '{tool_name}' is disabled in this workspace. "
        f"You MUST use the MCP tool '{correct_tool}' instead. {hint}"
    )
    return json.dumps(
        {
            "permission": "deny",
            "hookSpecificOutput": {
                "hookEventName": "BeforeTool",
                "permissionDecision": "deny",
                "message": message,
            },
        }
    )


def _allow_response() -> str:
    """Build a BeforeTool allow JSON response."""
    return json.dumps({"permission": "allow"})


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload: dict = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Never block the agent on a parse failure — fail open.
        print(_allow_response())
        return

    tool_name: str = payload.get("tool_name", "")

    if tool_name in ENFORCEMENT_MAP:
        correct_tool, hint = ENFORCEMENT_MAP[tool_name]
        print(_deny_response(tool_name, correct_tool, hint))
    else:
        print(_allow_response())


if __name__ == "__main__":
    main()
