from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app


def test_cli_autoharness_selftest() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["scripts", "autoharness", "--selftest"])
    assert result.exit_code == 0
    assert "pass:" in result.output


def test_cli_autoharness_stage_and_promote(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOHARNESS_PROJECT_ROOT", str(tmp_path))
    (tmp_path / ".agents" / "skills").mkdir(parents=True)

    runner = CliRunner()
    stage_res = runner.invoke(
        app,
        [
            "scripts",
            "autoharness",
            "stage",
            "create",
            "cli-test-skill",
            "--body",
            "---\nname: cli-test-skill\ndescription: Use when testing CLI commands.\ncategory: testing\n---\n# CLI Test\nBody",
            "--reason",
            "Test CLI staging",
            "--evidence",
            "Command failed with exit code 1",
        ],
    )
    assert stage_res.exit_code == 0
    assert "staged intent" in stage_res.output

    promote_res = runner.invoke(app, ["scripts", "autoharness", "promote", "--json"])
    assert promote_res.exit_code == 0
    assert "cli-test-skill" in promote_res.output
    assert (tmp_path / ".agents" / "skills" / "cli-test-skill" / "SKILL.md").is_file()


def test_cli_autoharness_check_links(tmp_path: Path) -> None:
    (tmp_path / "valid.md").write_text("# Doc\nNo broken links.", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app, ["scripts", "autoharness", "check-links", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "pass:" in result.output
