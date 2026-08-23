"""Tests for the guard_destructive.py PreToolUse safety hook template.

Drives the actual template script via subprocess (as Antigravity would),
feeding JSON payloads on stdin and asserting the JSON decision on stdout.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "buddhi"
    / "templates"
    / "agents"
    / "hooks"
    / "guard_destructive.py"
)


def run_hook(stdin_text: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def run_command_payload(command: str, shape: str = "command") -> dict:
    if shape == "command":
        payload = {"command": command}
    elif shape == "input.command":
        payload = {"input": {"command": command}}
    elif shape == "tool_input.command":
        payload = {"tool_input": {"command": command}}
    else:
        raise ValueError(shape)
    return run_hook(json.dumps(payload))


def test_ordinary_command_allowed() -> None:
    assert run_command_payload("ls -la") == {"decision": "allow"}


def test_rm_rf_root_denied() -> None:
    result = run_command_payload("rm -rf /")
    assert result["decision"] == "deny"


def test_rm_rf_relative_path_allowed() -> None:
    assert run_command_payload("rm -rf ./node_modules") == {"decision": "allow"}
    assert run_command_payload("rm -rf build/") == {"decision": "allow"}


def test_git_push_force_denied_without_confirm() -> None:
    result = run_command_payload("git push --force origin main")
    assert result["decision"] == "deny"


def test_git_push_force_allowed_with_confirm_marker() -> None:
    result = run_command_payload("git push --force origin main # CONFIRMED")
    assert result == {"decision": "allow"}


def test_git_reset_hard_denied() -> None:
    result = run_command_payload("git reset --hard HEAD~1")
    assert result["decision"] == "deny"


def test_git_reset_hard_allowed_with_confirm_marker() -> None:
    result = run_command_payload("git reset --hard HEAD~1 # CONFIRMED")
    assert result == {"decision": "allow"}


def test_drop_table_denied() -> None:
    result = run_command_payload("DROP TABLE users;")
    assert result["decision"] == "deny"


def test_truncate_table_denied() -> None:
    result = run_command_payload("TRUNCATE TABLE users;")
    assert result["decision"] == "deny"


def test_drop_database_denied() -> None:
    result = run_command_payload("DROP DATABASE prod;")
    assert result["decision"] == "deny"


def test_drop_schema_denied() -> None:
    result = run_command_payload("DROP SCHEMA public;")
    assert result["decision"] == "deny"


def test_bare_truncate_denied() -> None:
    result = run_command_payload("TRUNCATE users;")
    assert result["decision"] == "deny"


def test_rm_split_flags_root_denied() -> None:
    result = run_command_payload("rm -r -f /")
    assert result["decision"] == "deny"


def test_rm_long_flags_root_denied() -> None:
    result = run_command_payload("rm --recursive --force /")
    assert result["decision"] == "deny"


def test_rm_rf_quoted_root_denied() -> None:
    result = run_command_payload('rm -rf "/"')
    assert result["decision"] == "deny"


def test_malformed_stdin_allows() -> None:
    result = run_hook("not json at all {{{")
    assert result == {"decision": "allow"}


def test_empty_stdin_allows() -> None:
    result = run_hook("")
    assert result == {"decision": "allow"}


def test_write_payload_mentioning_destructive_command_in_content_allows() -> None:
    """Regression for C2: a Write/Edit-shaped payload (no command field, just
    file content) that happens to mention a destructive command in its
    content must not be denied — the hook must only ever pattern-match an
    actual extracted command string, never arbitrary tool payloads.
    """
    payload = {
        "tool_input": {
            "file_path": ".agents/rules/harness-core.md",
            "content": (
                "Destructive operations - force-push, `git reset --hard`, "
                "dropping or truncating a database table - require "
                "explicit user confirmation first."
            ),
        }
    }
    result = run_hook(json.dumps(payload))
    assert result == {"decision": "allow"}


def test_alternate_command_field_shapes_are_checked() -> None:
    assert run_command_payload("rm -rf /", shape="input.command")["decision"] == "deny"
    assert run_command_payload("rm -rf /", shape="tool_input.command")["decision"] == "deny"
