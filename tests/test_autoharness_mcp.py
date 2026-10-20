from __future__ import annotations

from pathlib import Path

from buddhi.mcp.server import stage_skill


def test_stage_skill_mcp_validation_and_staging(tmp_path: Path) -> None:
    (tmp_path / ".agents" / "skills").mkdir(parents=True)

    # Invalid action
    err_act = stage_skill(action="invalid_action", name="test", cwd=str(tmp_path))
    assert "Error:" in err_act

    # Missing evidence
    err_ev = stage_skill(
        action="create",
        name="test-skill",
        body="body",
        reason="reason",
        evidence="",
        cwd=str(tmp_path),
    )
    assert "Error:" in err_ev

    # Valid staging
    res = stage_skill(
        action="create",
        name="mcp-staged-skill",
        body="---\nname: mcp-staged-skill\ndescription: Use when testing MCP tool.\ncategory: testing\n---\n# Title\nBody",
        reason="Testing MCP staging",
        evidence="Observed failure in log",
        cwd=str(tmp_path),
    )
    assert "[AutoHarness] Staged intent" in res
    q_file = tmp_path / ".agents" / "autoharness" / "intents" / "interactive.jsonl"
    assert q_file.is_file()
    assert "mcp-staged-skill" in q_file.read_text(encoding="utf-8")
