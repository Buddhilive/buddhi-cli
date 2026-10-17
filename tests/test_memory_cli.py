from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_buddhi_memory_cli_lifecycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    # 1. Status on clean workspace
    result = runner.invoke(app, ["memory", "status"])
    assert result.exit_code == 0
    assert "Memory Bundle Status" in result.output

    # 2. Add memory node
    code_file = tmp_path / "src" / "api.py"
    code_file.parent.mkdir(parents=True)
    code_file.write_text("def my_api(): pass\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "memory",
            "add",
            "--kind",
            "decision",
            "--title",
            "REST Endpoints",
            "--summary",
            "Use REST conventions.",
            "--body",
            "Detailed rationale here.",
            "--source",
            "src/api.py#L1-L1",
            "--tag",
            "api",
        ],
    )
    assert result.exit_code == 0
    assert "Saved memory concept" in result.output

    # 3. Validate bundle
    result = runner.invoke(app, ["memory", "validate"])
    assert result.exit_code == 0
    assert "PASS" in result.output

    # 4. Sync
    result = runner.invoke(app, ["memory", "sync"])
    assert result.exit_code == 0

    # 5. Compact
    result = runner.invoke(app, ["memory", "compact"])
    assert result.exit_code == 0

    # 6. JSON output
    result = runner.invoke(app, ["memory", "status", "--json"])
    assert result.exit_code == 0
    assert '"total_nodes": 1' in result.output
