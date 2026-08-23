#!/usr/bin/env python3
"""Mechanical PreToolUse safety hook: guard_destructive.py

Registered by ../hooks.json as a PreToolUse hook. Antigravity invokes this
script as `python .agents/hooks/guard_destructive.py` for every proposed
tool call, feeding the proposed call as JSON on stdin. This script decides
whether the call should proceed by printing a JSON decision to stdout:

    {"decision": "allow"}
    {"decision": "deny", "reason": "<why>"}

This is a mechanical backstop for the "destructive operations require
confirmation" rule in ../rules/harness-core.md. It is deliberately simple
(stdlib only, no dependencies) and meant to be hand-edited: add your own
project's destructive patterns to DENY_RULES below as needed. Re-running
`buddhi init` will not clobber local edits to this file.

Safety contract: this script must never crash and must never block tool use
on account of its own bugs. Any failure to parse the input, or any
unexpected payload shape, falls back to {"decision": "allow"}.
"""

import json
import re
import sys

# The literal substring an agent can add to a command, after getting
# explicit user confirmation, to opt out of a deny rule that supports it
# (see the per-rule CONFIRMABLE flag below). Matched case-sensitively so it
# reads as a deliberate marker, not an accidental word in a path or message.
CONFIRMED_MARKER = "CONFIRMED"

# Each rule is (compiled_regex, reason, confirmable):
#   - compiled_regex: matched against the extracted command, case-insensitive.
#   - reason: short human-readable string returned in the deny decision.
#   - confirmable: if True, a command containing CONFIRMED_MARKER is exempt
#     from this rule; if False, the rule always denies on match.
DENY_RULES = [
    (
        re.compile(
            r"\brm\s+-(?:rf|fr)\b(?:\s+-\S+)*\s+(?:/|~)(?:/|\*)?(?:\s|$)",
            re.IGNORECASE,
        ),
        "rm -rf/-fr targeting root or home directory",
        False,
    ),
    (
        re.compile(
            r"\bgit\s+push\b.*(?:--force(?:-with-lease)?(?:=\S+)?\b|(?<!\S)-f\b)",
            re.IGNORECASE,
        ),
        "git push with --force/--force-with-lease/-f",
        True,
    ),
    (
        re.compile(r"\bgit\s+reset\b.*--hard\b", re.IGNORECASE),
        "git reset --hard",
        True,
    ),
    (
        re.compile(r"\b(?:DROP|TRUNCATE)\s+TABLE\b", re.IGNORECASE),
        "DROP TABLE / TRUNCATE TABLE",
        True,
    ),
    (
        re.compile(r"\bmkfs\b|\bdiskpart\b|\bformat ", re.IGNORECASE),
        "disk format/partition command (mkfs/diskpart/format)",
        False,
    ),
    (
        re.compile(r"\bterraform\s+destroy\b", re.IGNORECASE),
        "terraform destroy",
        True,
    ),
    (
        re.compile(r"(?=.*\bkubectl\s+delete\b)(?=.*\bprod)", re.IGNORECASE),
        "kubectl delete against a production namespace",
        True,
    ),
]


def extract_command(payload):
    """Pull the shell command string out of a tool-call payload.

    The field holding the command text varies by tool/hook shape, so check
    a few known locations in order. If none are present (or the payload
    isn't a dict), fall back to stringifying the whole payload so pattern
    matching still has something to look at.
    """
    if isinstance(payload, dict):
        command = payload.get("command")
        if isinstance(command, str):
            return command

        for outer_key, inner_key in (
            ("input", "command"),
            ("tool_input", "command"),
            ("parameters", "command"),
        ):
            outer = payload.get(outer_key)
            if isinstance(outer, dict):
                inner = outer.get(inner_key)
                if isinstance(inner, str):
                    return inner

    return json.dumps(payload)


def decide(payload):
    command = extract_command(payload)

    for pattern, reason, confirmable in DENY_RULES:
        if pattern.search(command):
            if confirmable and CONFIRMED_MARKER in command:
                continue
            return {"decision": "deny", "reason": reason}

    return {"decision": "allow"}


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
        result = decide(payload)
    except Exception:
        # Never block tool use because this hook itself is broken or the
        # input was malformed/non-JSON.
        result = {"decision": "allow"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
