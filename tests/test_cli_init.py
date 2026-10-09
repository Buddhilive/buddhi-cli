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
    expected_skills = (
        "repoagent-doc-generation",
        "okf-context",
        "system-design",
        "document-codebase",
        "plan",
        "specify",
        "tasks",
        "implement",
        "quick-plan",
        "verify",
        "debug",
        "ask",
        "remember",
        "status",
    )
    for skill_name in expected_skills:
        assert (agents_dir / "skills" / skill_name / "SKILL.md").exists()

    assert not (agents_dir / "workflows").exists()
    assert (agents_dir / "rules" / "okf-docs.md").exists()
    assert (agents_dir / "rules" / "harness-core.md").exists()
    assert (agents_dir / "templates" / "spec-template.md").exists()
    assert (agents_dir / "templates" / "plan-template.md").exists()
    assert (agents_dir / "templates" / "tasks-template.md").exists()
    assert (agents_dir / "templates" / "checklist-template.md").exists()
    assert (agents_dir / "templates" / "agents-template.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert "AGENTS.md" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert (agents_dir / "memory" / "user-preferences.md").exists()
    assert (agents_dir / "memory" / "project-conventions.md").exists()
    assert (agents_dir / "memory" / "tech-decisions.md").exists()
    assert (agents_dir / "memory" / "feedback-history.md").exists()
    assert (agents_dir / "mcp_config.json").exists()
    mcp_cfg = json.loads((agents_dir / "mcp_config.json").read_text(encoding="utf-8"))
    assert "mcpServers" in mcp_cfg
    assert mcp_cfg["mcpServers"]["buddhi"]["command"] == "buddhi-mcp"
    assert mcp_cfg["mcpServers"]["buddhi"]["args"] == ["--root", str(tmp_path.resolve())]
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

    assert not (agents_dir / "__init__.py").exists()
    assert not any(agents_dir.rglob("__pycache__"))


def test_init_is_idempotent_and_never_overwrites_agents_files(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def helper():\n    pass\n")

    result1 = runner.invoke(app, ["init", str(tmp_path)])
    assert result1.exit_code == 0, result1.output

    rule_path = tmp_path / ".agents" / "rules" / "okf-docs.md"
    rule_path.write_text("# customized by the user\n", encoding="utf-8")

    hook_path = tmp_path / ".agents" / "hooks" / "guard_destructive.py"
    hook_path.write_text("# customized by the user\n", encoding="utf-8")

    result2 = runner.invoke(app, ["init", str(tmp_path)])
    assert result2.exit_code == 0, result2.output

    assert rule_path.read_text(encoding="utf-8") == "# customized by the user\n"
    assert hook_path.read_text(encoding="utf-8") == "# customized by the user\n"


def test_init_migrates_and_removes_legacy_workflows(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def helper():\n    pass\n")

    # Simulate an existing project with legacy workflows
    workflows_dir = tmp_path / ".agents" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "plan.md").write_text("---\nname: plan\n---\n# Legacy Plan\n", encoding="utf-8")
    (workflows_dir / "custom-flow.md").write_text("# Custom User Flow\nDo step A and B.\n", encoding="utf-8")
    manifest = tmp_path / ".agents" / "workflows.json"
    manifest.write_text(json.dumps([{"name": "custom-flow", "path": "workflows/custom-flow.md"}]), encoding="utf-8")

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".agents"
    # Bundled plan skill was scaffolded
    assert (agents_dir / "skills" / "plan" / "SKILL.md").exists()
    # Custom flow was migrated to a skill with generated frontmatter
    custom_skill = agents_dir / "skills" / "custom-flow" / "SKILL.md"
    assert custom_skill.exists()
    custom_content = custom_skill.read_text(encoding="utf-8")
    assert "name: custom-flow" in custom_content
    assert "description:" in custom_content
    assert "# Custom User Flow" in custom_content

    # Legacy workflow files and directory completely removed to prevent conflicts
    assert not (agents_dir / "workflows").exists()

    # Empty manifest removed
    assert not manifest.exists()


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
