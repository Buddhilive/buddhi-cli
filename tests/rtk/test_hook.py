from __future__ import annotations

from buddhi.scripts.rtk.hook_handler import handle_hook_payload


def test_hook_rewrites_run_command_tool() -> None:
    payload = {
        "toolCall": {"name": "run_command", "args": {"CommandLine": "git status"}}
    }
    response = handle_hook_payload(payload)
    assert "overwrite" in response
    assert (
        "buddhi scripts rtk run -- git status" in response["overwrite"]["CommandLine"]
    )


def test_hook_leaves_non_shell_tool_alone() -> None:
    payload = {"toolCall": {"name": "read_file", "args": {"Path": "/some/file.txt"}}}
    response = handle_hook_payload(payload)
    assert response == {}


def test_hook_leaves_piped_command_alone() -> None:
    payload = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git log | grep fix"},
        }
    }
    response = handle_hook_payload(payload)
    assert response == {}


def test_hook_fail_open_on_corrupt_payload() -> None:
    response = handle_hook_payload("invalid string not dict")  # type: ignore
    assert response == {}
