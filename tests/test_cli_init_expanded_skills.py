import re
from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()

NEW_SKILLS_23 = [
    "explore-unknowns",
    "auto-research",
    "refactor-clean",
    "write-tests",
    "audit-tests",
    "audit-performance",
    "ratchet-files",
    "code-review",
    "write-docs",
    "review",
    "audit-choices",
    "handoff-spec",
    "close-spec",
    "eli5",
    "retro",
    "marketing-pages",
    "compare-screenshots",
    "design-with-images",
    "preview-shots",
    "screenshot-critique",
    "audit-agents",
    "eval-skills",
    "write-skills",
]

CUSTOM_SKILLS_NOT_IN_INIT = [
    "repo-to-skill",
    "renderer",
    "launch-video",
    "cinematic-shot",
    "isometric-motion",
    "xiaohei-illustrations",
]


def test_init_scaffolds_all_23_new_skills_and_preserves_customizations(tmp_path: Path):
    # Create sample codebase
    (tmp_path / "main.py").write_text("print('hello world')\n", encoding="utf-8")

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, f"init failed: {result.stdout}\n{result.stderr}"

    skills_dir = tmp_path / ".agents" / "skills"
    assert skills_dir.is_dir()

    # 1. Assert all 23 new skills exist with valid frontmatter
    for skill_name in NEW_SKILLS_23:
        skill_dir = skills_dir / skill_name
        assert skill_dir.is_dir(), f"Skill directory missing: {skill_name}"
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.is_file(), f"SKILL.md missing for: {skill_name}"
        content = skill_file.read_text(encoding="utf-8")

        m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
        assert m is not None, f"YAML frontmatter missing in {skill_name}/SKILL.md"
        fm = m.group(1)
        assert (
            f"name: {skill_name}" in fm
            or f"name: '{skill_name}'" in fm
            or f'name: "{skill_name}"' in fm
        ), f"name mismatch in {skill_name}"
        assert "description:" in fm, f"description missing in {skill_name}"

    # 2. Assert selective custom skills are NOT copied by init
    for custom_skill in CUSTOM_SKILLS_NOT_IN_INIT:
        assert not (skills_dir / custom_skill).exists(), (
            f"Custom skill {custom_skill} should not be in init"
        )

    # 3. Assert supporting reference files were copied
    assert (
        skills_dir / "explore-unknowns" / "references" / "stage-1-known-knowns.md"
    ).is_file()
    assert (
        skills_dir / "compare-screenshots" / "references" / "reference-landmarks.md"
    ).is_file()
    assert (skills_dir / "audit-agents" / "assets" / "example-agents.md").is_file()

    # 4. Modify a skill file to test idempotency
    target_skill_file = skills_dir / "explore-unknowns" / "SKILL.md"
    custom_content = "# CUSTOMIZED BY USER\n" + target_skill_file.read_text(
        encoding="utf-8"
    )
    target_skill_file.write_text(custom_content, encoding="utf-8")

    # Re-run init
    result2 = runner.invoke(app, ["init", str(tmp_path)])
    assert result2.exit_code == 0

    # Ensure custom content was preserved (not overwritten)
    assert target_skill_file.read_text(encoding="utf-8").startswith(
        "# CUSTOMIZED BY USER"
    )
