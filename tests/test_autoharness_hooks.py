from __future__ import annotations

from pathlib import Path

from buddhi.templates.agents.hooks.autoharness_hook import (
    handle_pre_tool_use,
    handle_session_start,
)


def test_hook_pre_tool_use_child_guard(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTOHARNESS_CHILD_SESSION", "1")
    payload = {
        "toolCall": {"name": "write_file", "args": {"Path": str(tmp_path / "foo.txt")}}
    }
    res = handle_pre_tool_use(tmp_path, payload)
    assert res.get("decision") == "deny"
    assert "read-only" in res.get("reason", "")


def test_hook_pre_tool_use_allow_main(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AUTOHARNESS_CHILD_SESSION", raising=False)
    payload = {
        "toolCall": {"name": "read_file", "args": {"Path": str(tmp_path / "foo.txt")}}
    }
    res = handle_pre_tool_use(tmp_path, payload)
    assert res.get("decision") == "allow"


def test_hook_session_start_contract(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".agents"
    skills_dir = agents_dir / "skills"
    skills_dir.mkdir(parents=True)

    payload = {"conversationId": "test-conv"}
    res = handle_session_start(tmp_path, payload)
    assert isinstance(res, dict)
