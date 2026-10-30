from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_init_scaffolds_a11y_rule_and_skill(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    # Check rule file
    rule_file = tmp_path / ".agents" / "rules" / "a11y.md"
    assert rule_file.is_file(), "rules/a11y.md should be scaffolded"
    rule_content = rule_file.read_text(encoding="utf-8")
    assert "name: a11y" in rule_content

    # Check skill file
    skill_file = tmp_path / ".agents" / "skills" / "a11y" / "SKILL.md"
    assert skill_file.is_file(), "skills/a11y/SKILL.md should be scaffolded"
    skill_content = skill_file.read_text(encoding="utf-8")
    assert "name: a11y" in skill_content
    assert "version: 2.5.0" in skill_content

    # Check 31 reference guides
    ref_dir = tmp_path / ".agents" / "skills" / "a11y" / "references"
    assert ref_dir.is_dir()
    guides = list(ref_dir.glob("guide-*.md"))
    assert len(guides) == 31, f"Expected 31 guides, found {len(guides)}"

    # Check 4 templates
    tpl_dir = tmp_path / ".agents" / "skills" / "a11y" / "templates"
    assert tpl_dir.is_dir()
    for name in ("REPORT.md", "EXCEPTIONS.md", "A11Y-DECISIONS.md", "ACCESSIBILITY.md"):
        assert (tpl_dir / name).is_file(), f"Missing template {name}"


def test_init_is_idempotent_for_a11y(tmp_path: Path) -> None:
    # First init
    res1 = runner.invoke(app, ["init", str(tmp_path)])
    assert res1.exit_code == 0

    rule_file = tmp_path / ".agents" / "rules" / "a11y.md"
    rule_file.write_text("custom user content", encoding="utf-8")

    # Second init
    res2 = runner.invoke(app, ["init", str(tmp_path)])
    assert res2.exit_code == 0

    # User modifications must be preserved
    assert rule_file.read_text(encoding="utf-8") == "custom user content"
