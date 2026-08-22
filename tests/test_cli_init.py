import json
from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_init_end_to_end_scaffolds_graph_docs_plan_and_agents(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def helper():\n    pass\n\ndef run():\n    helper()\n")

    result = runner.invoke(app, ["init", str(tmp_path)])

    assert result.exit_code == 0, result.output

    graphs_dir = tmp_path / ".buddhi" / "graphs"
    assert (graphs_dir / "tree-graph.json").exists()
    assert (graphs_dir / "tree-graph.db").exists()
    assert (graphs_dir / "tree-graph.html").exists()

    plan_path = tmp_path / ".buddhi" / "docs-plan.json"
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert len(plan) >= 2
    assert all("needs_generation" in entry for entry in plan)

    agents_dir = tmp_path / ".agents"
    assert (agents_dir / "skills" / "repoagent-doc-generation" / "SKILL.md").exists()
    assert (agents_dir / "skills" / "okf-context" / "SKILL.md").exists()
    assert (agents_dir / "workflows" / "document-codebase.md").exists()
    assert (agents_dir / "rules" / "okf-docs.md").exists()
    assert (agents_dir / "rules" / "harness-core.md").exists()
    assert (agents_dir / "workflows" / "plan.md").exists()
    assert (agents_dir / "skills" / "README.md").exists()
    for specialist in (
        "frontend-specialist",
        "backend-specialist",
        "database-specialist",
        "testing-specialist",
        "security-specialist",
        "deployment-specialist",
        "git-specialist",
        "terminal-runner",
    ):
        assert (agents_dir / "agents" / f"{specialist}.md").exists()


def test_init_is_idempotent_and_never_overwrites_agents_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def helper():\n    pass\n")

    result1 = runner.invoke(app, ["init", str(tmp_path)])
    assert result1.exit_code == 0, result1.output

    rule_path = tmp_path / ".agents" / "rules" / "okf-docs.md"
    rule_path.write_text("# customized by the user\n", encoding="utf-8")

    result2 = runner.invoke(app, ["init", str(tmp_path)])
    assert result2.exit_code == 0, result2.output

    assert rule_path.read_text(encoding="utf-8") == "# customized by the user\n"


def test_init_bad_path_errors_cleanly(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    result = runner.invoke(app, ["init", str(missing)])

    assert result.exit_code == 1
    assert not (missing / ".agents").exists()


def test_docs_plan_command_runs_standalone(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def helper():\n    pass\n")

    result = runner.invoke(app, ["docs", "plan", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".buddhi" / "docs-plan.json").exists()
