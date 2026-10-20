from __future__ import annotations

from pathlib import Path

from buddhi.scripts.autoharness.intent_queue import append_intent, read_intents
from buddhi.scripts.autoharness.models import SkillIntent
from buddhi.scripts.autoharness.promoter import drain_and_promote
from buddhi.scripts.autoharness.sidecar import is_agent_created, read_sidecar
from buddhi.scripts.autoharness.validate import validate_skill_candidate


def test_sidecar_ownership_barrier(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".agents"
    skills_dir = agents_dir / "skills"
    skills_dir.mkdir(parents=True)

    # Native skill without created_by: 'agent'
    native_dir = skills_dir / "specify"
    native_dir.mkdir()
    (native_dir / "SKILL.md").write_text(
        "---\nname: specify\ndescription: Native spec.\n---\nBody", encoding="utf-8"
    )
    assert is_agent_created(native_dir) is False

    intent = SkillIntent(
        action="patch",
        name="specify",
        old_string="Body",
        new_string="New Body",
        reason="Illegal attempt to mutate native skill",
        evidence="Evidence",
    )
    res = validate_skill_candidate(
        intent=intent,
        assembled_body="New Body",
        target_is_agent_created=False,
        target_exists=True,
        layer_root=agents_dir,
    )
    assert res.valid is False
    assert any(f.code == "self_produced" for f in res.findings)


def test_promoter_create_and_patch(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".agents"
    skills_dir = agents_dir / "skills"
    skills_dir.mkdir(parents=True)

    body = (
        "---\n"
        "name: python-tester\n"
        "description: Use when running pytest tests.\n"
        "category: testing\n"
        "---\n"
        "# Python Tester\n"
        "Run `pytest`.\n"
    )
    intent = SkillIntent(
        action="create",
        name="python-tester",
        body=body,
        files={"references/tips.md": "# Tips\nUse -q flag."},
        reason="Distilled pytest workflow",
        evidence="pytest failed with exit status 1",
    )
    append_intent(intent, "test-run", project_root=tmp_path)
    queued = read_intents("project", "test-run", project_root=tmp_path)
    assert len(queued) == 1

    account = drain_and_promote("project", "test-run", project_root=tmp_path)
    assert "python-tester" in account.landed
    assert (skills_dir / "python-tester" / "SKILL.md").is_file()
    assert (skills_dir / "python-tester" / "references" / "tips.md").is_file()
    assert is_agent_created(skills_dir / "python-tester") is True

    sidecar = read_sidecar(skills_dir / "python-tester")
    assert sidecar is not None
    assert sidecar.created_by == "agent"
    assert sidecar.patch == 0

    # Test patch
    patch_intent = SkillIntent(
        action="patch",
        name="python-tester",
        old_string="Run `pytest`.",
        new_string="Run `uv run pytest`.",
        reason="Updated to uv",
        evidence="User prefers uv run",
    )
    append_intent(patch_intent, "test-patch-run", project_root=tmp_path)
    account_patch = drain_and_promote(
        "project", "test-patch-run", project_root=tmp_path
    )
    assert "python-tester" in account_patch.landed

    updated_body = (skills_dir / "python-tester" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "Run `uv run pytest`." in updated_body

    updated_sidecar = read_sidecar(skills_dir / "python-tester")
    assert updated_sidecar is not None
    assert updated_sidecar.patch == 1
