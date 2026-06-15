"""
gate_io — Universal I/O Blocker for Antigravity PreToolUse hooks.

Intercepts native file-read and search tool calls (view_file, grep_search,
find_by_name) and issues a deterministic DENY response, redirecting the
agent to the token-optimized buddhi_search / buddhi_read MCP tools.

Protocol:
  1. Read JSON from stdin (Antigravity hook payload).
  2. Extract the tool name from toolCall.name.
  3. Emit a deny decision on stdout with a redirect message.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Tools that this hook intercepts
_GATED_TOOLS: frozenset[str] = frozenset(
    [
        "grep_search",
        "find_by_name",
    ]
)

# Mapping from gated tool → recommended buddhi alternative
_REDIRECT_MAP: dict[str, str] = {
    "grep_search": "buddhi_search",
    "find_by_name": "buddhi_read",
}


def _build_deny_payload(tool_name: str, args: dict) -> dict:
    """Construct the deny decision JSON payload."""
    redirect = _REDIRECT_MAP.get(tool_name, "buddhi_search")

    # Build a context-aware hint based on the intercepted arguments
    hint_parts: list[str] = []
    if tool_name == "grep_search":
        query = args.get("Query") or args.get("pattern") or ""
        if query:
            hint_parts.append(
                f"To search for '{query}', call `{redirect}(query=\"{query}\")` instead."
            )
        else:
            hint_parts.append(f"Use `{redirect}(query=<search_term>)` instead.")
    elif tool_name == "find_by_name":
        name = args.get("Name") or args.get("name") or ""
        if name:
            hint_parts.append(
                f"To locate '{name}', call `{redirect}(query=\"{name}\")` instead."
            )
        else:
            hint_parts.append(f"Use `{redirect}(query=<identifier>)` instead.")

    redirect_hint = " ".join(hint_parts)

    return {
        "decision": "deny",
        "reason": (
            f"Direct filesystem search/read tools are disabled to enforce your token budget. "
            f"{redirect_hint} "
            f"These tools are exposed on your active MCP server (`buddhi-cli`)."
        ),
    }


def _check_and_consume_fallback(tool_name: str) -> bool:
    """Checks if a fallback is allowed for the tool, and consumes it if True."""
    fallback_path = Path(".buddhi/fallback_allowed.json")
    if not fallback_path.exists():
        return False
    try:
        with open(fallback_path, "r", encoding="utf-8") as f:
            allowed = json.load(f)
        if allowed.get(tool_name):
            # Consume the fallback permission so it only works for the immediate next execution
            allowed[tool_name] = False
            with open(fallback_path, "w", encoding="utf-8") as f:
                json.dump(allowed, f)
            return True
    except Exception:
        pass
    return False


def main() -> None:
    """Entrypoint for the hook script."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            # Empty payload — allow by default (shouldn't happen)
            json.dump({"decision": "allow"}, sys.stdout)
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # Malformed input — allow to avoid breaking the agent
            json.dump({"decision": "allow"}, sys.stdout)
            return

        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        if tool_name in _GATED_TOOLS:
            if _check_and_consume_fallback(tool_name):
                response = {"decision": "allow"}
            else:
                response = _build_deny_payload(tool_name, tool_args)
        else:
            # Not a gated tool — passthrough
            response = {"decision": "allow"}

        json.dump(response, sys.stdout)
    except Exception:
        # Fallback gracefully
        json.dump({"decision": "allow"}, sys.stdout)


if __name__ == "__main__":
    main()
