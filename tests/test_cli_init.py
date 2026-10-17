import json
from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_init_end_to_end_scaffolds_graph_docs_plan_and_agents(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def helper():\n    pass\n\ndef run():\n    helper()\n"
    )

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
        "spec-plan",
        "specify",
        "spec-tasks",
        "implement",
        "quick-plan",
        "verify",
        "debug",
        "ask",
        "remember",
        "status",
        "antislop",
        "antislop-ui",
        "antislop-copywriting",
        "antislop-human",
        "antislop-layoutmobile",
        "antislop-code",
    )
    for skill_name in expected_skills:
        assert (agents_dir / "skills" / skill_name / "SKILL.md").exists()

    assert not (agents_dir / "skills" / "plan").exists()
    assert not (agents_dir / "skills" / "tasks").exists()
    assert not (agents_dir / "workflows").exists()
    assert (agents_dir / "rules" / "okf-docs.md").exists()
    assert (agents_dir / "rules" / "harness-core.md").exists()
    assert (agents_dir / "rules" / "antislop.md").exists()
    assert (agents_dir / "templates" / "spec-template.md").exists()
    assert (agents_dir / "templates" / "plan-template.md").exists()
    assert (agents_dir / "templates" / "tasks-template.md").exists()
    assert (agents_dir / "templates" / "checklist-template.md").exists()
    assert (agents_dir / "templates" / "agents-template.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert "AGENTS.md" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert (agents_dir / "memory" / "MEMORY.md").exists()
    assert (agents_dir / "memory" / "log.md").exists()
    assert (agents_dir / "memory" / "decisions" / "index.md").exists()
    assert (agents_dir / "memory" / "conventions" / "index.md").exists()
    assert (agents_dir / "memory" / "preferences" / "index.md").exists()
    assert (agents_dir / "memory" / "feedback" / "index.md").exists()
    assert (agents_dir / "memory" / "sdd" / "index.md").exists()
    assert (agents_dir / "mcp_config.json").exists()
    mcp_cfg = json.loads((agents_dir / "mcp_config.json").read_text(encoding="utf-8"))
    assert "mcpServers" in mcp_cfg
    assert mcp_cfg["mcpServers"]["buddhi"]["command"] == "buddhi-mcp"
    assert mcp_cfg["mcpServers"]["buddhi"]["args"] == [
        "--root",
        str(tmp_path.resolve()),
    ]
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
    assert "antislop" in (agents_dir / "agents" / "frontend-specialist.md").read_text(
        encoding="utf-8"
    )

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
    (workflows_dir / "plan.md").write_text(
        "---\nname: plan\n---\n# Legacy Plan\n", encoding="utf-8"
    )
    (workflows_dir / "custom-flow.md").write_text(
        "# Custom User Flow\nDo step A and B.\n", encoding="utf-8"
    )
    manifest = tmp_path / ".agents" / "workflows.json"
    manifest.write_text(
        json.dumps([{"name": "custom-flow", "path": "workflows/custom-flow.md"}]),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".agents"
    # Bundled spec-plan skill was scaffolded
    assert (agents_dir / "skills" / "spec-plan" / "SKILL.md").exists()
    assert not (agents_dir / "skills" / "plan").exists()
    assert not (agents_dir / "skills" / "tasks").exists()
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


def test_init_clean_directory_scaffolds_spec_plan_and_not_plan(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def run():\n    pass\n")

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".agents"
    spec_plan_skill = agents_dir / "skills" / "spec-plan" / "SKILL.md"
    legacy_plan_skill = agents_dir / "skills" / "plan"

    assert spec_plan_skill.exists()
    assert "name: spec-plan" in spec_plan_skill.read_text(encoding="utf-8")
    assert not legacy_plan_skill.exists()

    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "/spec-plan" in agents_md
    assert "/quick-plan" in agents_md
    assert "/plan " not in agents_md and "`/plan`" not in agents_md

    harness_core = (agents_dir / "rules" / "harness-core.md").read_text(
        encoding="utf-8"
    )
    assert "/spec-plan" in harness_core
    assert "`/plan`" not in harness_core


def test_init_migrates_existing_project_with_legacy_plan_skill(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def run():\n    pass\n")

    # Simulate existing project with legacy plan skill and user customization
    legacy_skill_dir = tmp_path / ".agents" / "skills" / "plan"
    legacy_skill_dir.mkdir(parents=True)
    custom_content = (
        "---\n"
        "name: plan\n"
        "description: User custom plan skill description\n"
        "---\n"
        "# Custom Plan Instructions\n"
        "Custom rule: Always produce sequence diagrams.\n"
    )
    (legacy_skill_dir / "SKILL.md").write_text(custom_content, encoding="utf-8")

    # Simulate existing AGENTS.md and harness-core.md with /plan references
    (tmp_path / "AGENTS.md").write_text(
        "1. `/specify` — feature branch\n"
        "2. `/plan` — synthesize technical architecture\n"
        "- Use `/quick-plan` for lightweight work.\n",
        encoding="utf-8",
    )
    rules_dir = tmp_path / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "harness-core.md").write_text(
        "Go through the `/plan` skill before any code is written.\n"
        "When `/plan` or other harness work surfaces a convention...\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".agents"
    assert not (agents_dir / "skills" / "plan").exists()
    assert not (agents_dir / "skills" / "tasks").exists()

    migrated_skill = agents_dir / "skills" / "spec-plan" / "SKILL.md"
    assert migrated_skill.exists()
    migrated_text = migrated_skill.read_text(encoding="utf-8")
    assert "name: spec-plan" in migrated_text
    assert "Custom rule: Always produce sequence diagrams." in migrated_text

    updated_agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "`/spec-plan`" in updated_agents
    assert "`/quick-plan`" in updated_agents
    assert "`/plan`" not in updated_agents

    updated_harness = (rules_dir / "harness-core.md").read_text(encoding="utf-8")
    assert "`/spec-plan`" in updated_harness
    assert "`/plan`" not in updated_harness


def test_init_clean_directory_scaffolds_spec_tasks_and_not_tasks(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("def run():\n    pass\n")

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".agents"
    spec_tasks_skill = agents_dir / "skills" / "spec-tasks" / "SKILL.md"
    legacy_tasks_skill = agents_dir / "skills" / "tasks"

    assert spec_tasks_skill.exists()
    assert "name: spec-tasks" in spec_tasks_skill.read_text(encoding="utf-8")
    assert not legacy_tasks_skill.exists()

    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "/spec-tasks" in agents_md
    assert "/tasks " not in agents_md and "`/tasks`" not in agents_md


def test_init_migrates_existing_project_with_legacy_tasks_skill(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def run():\n    pass\n")

    # Simulate existing project with legacy tasks skill and user customization
    legacy_skill_dir = tmp_path / ".agents" / "skills" / "tasks"
    legacy_skill_dir.mkdir(parents=True)
    custom_content = (
        "---\n"
        "name: tasks\n"
        "description: User custom tasks skill description with /tasks\n"
        "---\n"
        "# /tasks\n"
        "Custom rule: Always tag tests first.\n"
    )
    (legacy_skill_dir / "SKILL.md").write_text(custom_content, encoding="utf-8")

    # Simulate existing AGENTS.md with /tasks references
    (tmp_path / "AGENTS.md").write_text(
        "1. `/specify` — feature branch\n"
        "2. `/spec-plan` — synthesize technical architecture\n"
        "3. `/tasks` — break down tasks by user story in `tasks.md`\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".agents"
    assert not (agents_dir / "skills" / "tasks").exists()

    migrated_skill = agents_dir / "skills" / "spec-tasks" / "SKILL.md"
    assert migrated_skill.exists()
    migrated_text = migrated_skill.read_text(encoding="utf-8")
    assert "name: spec-tasks" in migrated_text
    assert "# /spec-tasks" in migrated_text
    assert "Custom rule: Always tag tests first." in migrated_text

    updated_agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "`/spec-tasks`" in updated_agents
    assert "`/tasks`" not in updated_agents
