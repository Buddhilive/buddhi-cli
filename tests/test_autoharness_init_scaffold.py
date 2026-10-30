from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app


def test_init_scaffolds_autoharness_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0

    agents_dir = tmp_path / ".agents"
    assert (agents_dir / "rules" / "autoharness.md").is_file()
    assert (agents_dir / "skills" / "learn" / "SKILL.md").is_file()
    assert (agents_dir / "skills" / "learn" / "references" / "format_spec.md").is_file()
    assert (agents_dir / "agents" / "reflector.md").is_file()
    assert (agents_dir / "agents" / "curator.md").is_file()
