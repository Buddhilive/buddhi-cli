from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_generate_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def helper():\n    pass\n\ndef run():\n    helper()\n")

    result = runner.invoke(app, ["generate", "--tree", str(tmp_path)])

    assert result.exit_code == 0, result.output
    graphs_dir = tmp_path / ".buddhi" / "graphs"
    assert (graphs_dir / "tree-graph.json").exists()
    assert (graphs_dir / "tree-graph.db").exists()
    assert (graphs_dir / "tree-graph.html").exists()
    assert (tmp_path / ".buddhi" / ".gitignore").read_text(encoding="utf-8") == "graphs/\n"


def test_generate_bad_path_errors_cleanly(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    result = runner.invoke(app, ["generate", "--tree", str(missing)])

    assert result.exit_code == 1
    assert not (missing / ".buddhi").exists()


def test_generate_path_that_is_a_file_errors(tmp_path: Path) -> None:
    a_file = tmp_path / "not_a_dir.py"
    a_file.write_text("x = 1\n")

    result = runner.invoke(app, ["generate", "--tree", str(a_file)])

    assert result.exit_code == 1


def test_generate_on_empty_project_still_writes_valid_artifacts(tmp_path: Path) -> None:
    result = runner.invoke(app, ["generate", "--tree", str(tmp_path)])

    assert result.exit_code == 0, result.output
    graphs_dir = tmp_path / ".buddhi" / "graphs"
    assert (graphs_dir / "tree-graph.json").exists()
    assert (graphs_dir / "tree-graph.db").exists()
    assert (graphs_dir / "tree-graph.html").exists()
