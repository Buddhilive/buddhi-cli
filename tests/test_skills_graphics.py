from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.skills.registry import GRAPHICS_SKILLS, get_skill

runner = CliRunner()


def test_graphics_skills_registered():
    assert len(GRAPHICS_SKILLS) == 5
    for skill_name in GRAPHICS_SKILLS:
        entry = get_skill(skill_name)
        assert entry is not None, f"Skill '{skill_name}' not found in registry"
        assert entry.flag == f"--{skill_name}"
        assert entry.target_dir_name == skill_name


def test_skills_table_displays_graphics_and_bundle():
    result = runner.invoke(app, ["skills"])
    assert result.exit_code == 0
    assert "renderer" in result.output
    assert "launch-video" in result.output
    assert "cinematic-shot" in result.output
    assert "isometric-motion" in result.output
    assert "xiaohei-illustrations" in result.output
    assert "--graphics" in result.output


def test_install_individual_graphics_skill(tmp_path: Path):
    result = runner.invoke(app, ["skills", "--renderer", "-p", str(tmp_path)])
    assert result.exit_code == 0
    skill_file = tmp_path / ".agents" / "skills" / "renderer" / "SKILL.md"
    assert skill_file.is_file()
    assert "name: renderer" in skill_file.read_text(encoding="utf-8")


def test_install_graphics_bundle(tmp_path: Path):
    result = runner.invoke(app, ["skills", "--graphics", "-p", str(tmp_path)])
    assert result.exit_code == 0

    skills_dir = tmp_path / ".agents" / "skills"
    for s in GRAPHICS_SKILLS:
        skill_dir = skills_dir / s
        assert skill_dir.is_dir(), f"Bundle missing skill dir: {s}"
        assert (skill_dir / "SKILL.md").is_file(), f"Bundle missing SKILL.md for: {s}"

    # Verify nested kit/scripts for isometric-motion
    iso_dir = skills_dir / "isometric-motion"
    assert (iso_dir / "references").is_dir()

    # Test idempotency (skip without force)
    result_skip = runner.invoke(app, ["skills", "--graphics", "-p", str(tmp_path)])
    assert result_skip.exit_code == 0
    assert "already exists" in result_skip.output

    # Test force overwrite
    result_force = runner.invoke(
        app, ["skills", "--renderer", "-p", str(tmp_path), "--force"]
    )
    assert result_force.exit_code == 0
    assert "updated" in result_force.output or "done" in result_force.output
