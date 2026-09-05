from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()



def test_skills_list():
    """Verify that running `buddhi skills` without arguments lists all custom skills."""
    result = runner.invoke(app, ["skills"])
    assert result.exit_code == 0
    assert "Available Custom Agent Skills" in result.stdout
    assert "repo-to-skill" in result.stdout
    assert "--repo-to-skill" in result.stdout
    assert "To install a skill" in result.stdout


def test_skills_install_repo_to_skill(tmp_path: Path):
    """Verify installing repo-to-skill into a target directory."""
    result = runner.invoke(app, ["skills", "--repo-to-skill", "-p", str(tmp_path)])
    assert result.exit_code == 0
    assert "added skill" in result.stdout
    assert "repo-to-skill" in result.stdout

    skill_dir = tmp_path / ".agents" / "skills" / "repo-to-skill"
    assert skill_dir.is_dir()
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file()
    content = skill_md.read_text(encoding="utf-8")
    assert "name: repo-to-skill" in content
    assert (skill_dir / "references" / "skill-format.md").is_file()
    assert (skill_dir / "references" / "eval-schemas.md").is_file()


def test_skills_install_skip_when_already_exists(tmp_path: Path):
    """Verify skipping without error when skill already exists and --force is not supplied."""
    res1 = runner.invoke(app, ["skills", "--repo-to-skill", "-p", str(tmp_path)])
    assert res1.exit_code == 0

    res2 = runner.invoke(app, ["skills", "--repo-to-skill", "-p", str(tmp_path)])
    assert res2.exit_code == 0
    assert "already exists" in res2.stdout
    assert "Skipping" in res2.stdout


def test_skills_install_force_overwrite(tmp_path: Path):
    """Verify overwriting when --force is supplied."""
    runner.invoke(app, ["skills", "--repo-to-skill", "-p", str(tmp_path)])
    skill_md = tmp_path / ".agents" / "skills" / "repo-to-skill" / "SKILL.md"
    skill_md.write_text("modified content", encoding="utf-8")

    res = runner.invoke(app, ["skills", "--repo-to-skill", "-p", str(tmp_path), "--force"])
    assert res.exit_code == 0
    assert "updated skill" in res.stdout
    content = skill_md.read_text(encoding="utf-8")
    assert content != "modified content"
    assert "name: repo-to-skill" in content


def test_skills_run_repo_to_skill(tmp_path: Path):
    """Verify running repo-to-skill analyzer on a local repository."""
    (tmp_path / "README.md").write_text(
        "# Demo Project\n\nA tool for tests.\n\n```bash\nuv run test\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n[project.scripts]\ndemo = 'demo:main'\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["skills", "run", "repo-to-skill", str(tmp_path)])
    assert result.exit_code == 0


    assert "Repository Analysis" in result.stdout
    assert "CLI Tool" in result.stdout


def test_skills_run_repo_to_skill_json(tmp_path: Path):
    """Verify running repo-to-skill analyzer with --json flag."""
    (tmp_path / "README.md").write_text("# Json Test\n\nTesting json output.\n", encoding="utf-8")

    result = runner.invoke(app, ["skills", "run", "repo-to-skill", str(tmp_path), "--json"])
    assert result.exit_code == 0
    import json

    data = json.loads(result.stdout)
    assert data["title"] == "Json Test"
    assert data["name"] == tmp_path.name


def test_skills_run_unknown_skill():
    """Verify error on unknown skill name."""
    result = runner.invoke(app, ["skills", "run", "nonexistent-skill", "."])
    assert result.exit_code == 1
    assert "unknown skill" in result.output


def test_skills_installed_script_direct_execution(tmp_path: Path):
    """Verify that the installed analyze_repo.py script executes directly via python."""
    import subprocess
    import sys

    target_project = tmp_path / "my_project"
    target_project.mkdir()
    (target_project / "README.md").write_text("# My Direct Project\n", encoding="utf-8")

    res_install = runner.invoke(app, ["skills", "--repo-to-skill", "-p", str(target_project)])
    assert res_install.exit_code == 0

    script_path = target_project / ".agents" / "skills" / "repo-to-skill" / "scripts" / "analyze_repo.py"
    assert script_path.is_file()

    res = subprocess.run(
        [sys.executable, str(script_path), str(target_project), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0

    import json

    data = json.loads(res.stdout)
    assert data["name"] == "my_project"


def test_init_does_not_install_custom_skills(tmp_path: Path):
    """Verify that buddhi init does not eagerly scaffold selective custom skills."""
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0

    agents_skills = tmp_path / ".agents" / "skills"
    assert agents_skills.is_dir()
    # Base harness skills exist
    assert (agents_skills / "okf-context").is_dir()
    # Selective custom skill must NOT be installed by init
    assert not (agents_skills / "repo-to-skill").exists()





