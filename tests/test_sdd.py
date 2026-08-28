from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_sdd_dry_run_create() -> None:
    dry_res = runner.invoke(
        app,
        [
            "sdd",
            "create",
            "--dry-run",
            "--short-name",
            "auth-feat",
            "--number",
            "2",
            "--json",
            "Feature description",
        ],
        catch_exceptions=False,
    )
    assert dry_res.exit_code == 0, dry_res.output
    data = json.loads(dry_res.output)
    assert data["BRANCH_NAME"] == "002-auth-feat"
    assert "spec.md" in data["SPEC_FILE"]
    assert data["DRY_RUN"] is True


def test_sdd_resolve_template_built_in() -> None:
    res = runner.invoke(app, ["sdd", "resolve-template", "spec-template", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["TEMPLATE_NAME"] == "spec-template"
    assert "Feature Specification" in data["TEMPLATE_CONTENT"]


def test_sdd_help_commands() -> None:
    for cmd in ["create", "setup-plan", "setup-tasks", "check", "resolve-template"]:
        res = runner.invoke(app, ["sdd", cmd, "--help"])
        assert res.exit_code == 0, f"sdd {cmd} --help failed: {res.output}"


def test_sdd_full_lifecycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text("def app():\n    pass\n")

    # 1. Initialize buddhi harness
    init_res = runner.invoke(app, ["init", str(tmp_path)])
    assert init_res.exit_code == 0, init_res.output

    # 2. SDD create feature
    create_res = runner.invoke(
        app,
        [
            "sdd",
            "create",
            "--short-name",
            "login",
            "--number",
            "1",
            "--json",
            "User login flow",
        ],
        catch_exceptions=False,
    )
    assert create_res.exit_code == 0, create_res.output
    create_data = json.loads(create_res.output)
    spec_path = Path(create_data["SPEC_FILE"])
    assert spec_path.is_file()
    assert "Feature Specification" in spec_path.read_text(encoding="utf-8")

    # 3. SDD setup-plan
    plan_res = runner.invoke(app, ["sdd", "setup-plan", "--json"], catch_exceptions=False)
    assert plan_res.exit_code == 0, plan_res.output
    plan_data = json.loads(plan_res.output)
    plan_path = Path(plan_data["IMPL_PLAN"])
    assert plan_path.is_file()
    assert "Implementation Plan" in plan_path.read_text(encoding="utf-8")

    # 4. SDD setup-tasks
    tasks_res = runner.invoke(app, ["sdd", "setup-tasks", "--json"], catch_exceptions=False)
    assert tasks_res.exit_code == 0, tasks_res.output
    tasks_data = json.loads(tasks_res.output)
    assert "TASKS_TEMPLATE_CONTENT" in tasks_data

    # Write tasks.md to satisfy prerequisites
    tasks_path = plan_path.parent / "tasks.md"
    tasks_path.write_text("# Tasks\n- [ ] T001 Setup\n", encoding="utf-8")

    # 5. SDD check prerequisites
    check_res = runner.invoke(
        app,
        ["sdd", "check", "--require-tasks", "--include-tasks", "--json"],
        catch_exceptions=False,
    )
    assert check_res.exit_code == 0, check_res.output
    check_data = json.loads(check_res.output)
    assert "tasks.md" in check_data["AVAILABLE_DOCS"]
