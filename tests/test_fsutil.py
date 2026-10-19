import json
from pathlib import Path

from buddhi.util.fsutil import (
    ensure_buddhi_dirs,
    migrate_legacy_plan_skill,
    migrate_legacy_workflows,
    sync_template_tree,
)


def test_creates_buddhi_and_graphs_dirs(tmp_path: Path) -> None:
    graphs_dir = ensure_buddhi_dirs(tmp_path)

    assert (tmp_path / ".buddhi").is_dir()
    assert graphs_dir == tmp_path / ".buddhi" / "graphs"
    assert graphs_dir.is_dir()


def test_creates_gitignore_with_graphs_content(tmp_path: Path) -> None:
    ensure_buddhi_dirs(tmp_path)

    gitignore = tmp_path / ".buddhi" / ".gitignore"
    assert gitignore.read_text(encoding="utf-8") == "graphs/\n"


def test_does_not_overwrite_existing_gitignore(tmp_path: Path) -> None:
    buddhi_dir = tmp_path / ".buddhi"
    buddhi_dir.mkdir()
    gitignore = buddhi_dir / ".gitignore"
    gitignore.write_text("custom content\n", encoding="utf-8")

    ensure_buddhi_dirs(tmp_path)

    assert gitignore.read_text(encoding="utf-8") == "custom content\n"


def test_idempotent_on_rerun(tmp_path: Path) -> None:
    ensure_buddhi_dirs(tmp_path)
    ensure_buddhi_dirs(tmp_path)  # should not raise

    assert (tmp_path / ".buddhi" / "graphs").is_dir()


def test_sync_template_tree_copies_non_md_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Create non-.md files
    (src_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")
    (src_dir / "script.py").write_text("print('hello')", encoding="utf-8")

    report = sync_template_tree(src_dir, dest_dir)

    # Check that non-.md files were copied
    assert (dest_dir / "config.json").exists()
    assert (dest_dir / "script.py").exists()
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == '{"key": "value"}'
    assert (dest_dir / "script.py").read_text(encoding="utf-8") == "print('hello')"
    assert len(report.created) == 2
    assert len(report.kept_existing) == 0


def test_sync_template_tree_copies_both_md_and_non_md_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Create both .md and non-.md files
    (src_dir / "readme.md").write_text("# README", encoding="utf-8")
    (src_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")
    (src_dir / "script.py").write_text("print('hello')", encoding="utf-8")

    report = sync_template_tree(src_dir, dest_dir)

    # Check that all files were copied
    assert (dest_dir / "readme.md").exists()
    assert (dest_dir / "config.json").exists()
    assert (dest_dir / "script.py").exists()
    assert (dest_dir / "readme.md").read_text(encoding="utf-8") == "# README"
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == '{"key": "value"}'
    assert (dest_dir / "script.py").read_text(encoding="utf-8") == "print('hello')"
    assert len(report.created) == 3
    assert len(report.kept_existing) == 0


def test_sync_template_tree_preserves_existing_non_md_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Pre-create a destination file with custom content
    (dest_dir / "config.json").write_text("custom content", encoding="utf-8")

    # Create the same file in source with different content
    (src_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")

    report = sync_template_tree(src_dir, dest_dir)

    # Check that the existing file was preserved and not overwritten
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == "custom content"
    assert len(report.created) == 0
    assert len(report.kept_existing) == 1
    assert (dest_dir / "config.json") in report.kept_existing


def test_sync_template_tree_skips_init_py_and_pycache(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # The template tree is a Python package: root __init__.py plus a stray
    # __pycache__ dir (present under a pip install, which byte-compiles).
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "hooks").mkdir()
    (src_dir / "hooks" / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "hooks" / "guard_destructive.py").write_text(
        "print('ok')", encoding="utf-8"
    )
    pycache_dir = src_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "foo.pyc").write_bytes(b"\x00\x01")

    report = sync_template_tree(src_dir, dest_dir)

    assert not (dest_dir / "__init__.py").exists()
    assert not (dest_dir / "hooks" / "__init__.py").exists()
    assert not any(dest_dir.rglob("__pycache__"))
    assert (dest_dir / "hooks" / "guard_destructive.py").exists()
    assert len(report.created) == 1


def test_migrate_legacy_workflows_converts_and_removes(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".agents"
    workflows_dir = agents_dir / "workflows"
    workflows_dir.mkdir(parents=True)

    # 1. Plain markdown without frontmatter
    (workflows_dir / "plain.md").write_text(
        "# Plain Flow\nRun these steps.\n", encoding="utf-8"
    )

    # 2. Markdown with frontmatter lacking description
    (workflows_dir / "no-desc.md").write_text(
        "---\nversion: 1.0\n---\n# No Desc\nBody.\n", encoding="utf-8"
    )

    # 3. Existing skill that should NOT be overwritten
    skills_dir = agents_dir / "skills" / "already-exists"
    skills_dir.mkdir(parents=True)
    existing_skill = skills_dir / "SKILL.md"
    existing_skill.write_text("# Existing Skill Kept\n", encoding="utf-8")
    (workflows_dir / "already-exists.md").write_text(
        "# Old Workflow\n", encoding="utf-8"
    )

    # 4. workflows.json manifest with one item to keep and one to remove
    manifest = agents_dir / "workflows.json"
    manifest.write_text(
        json.dumps([{"name": "plain"}, {"name": "keep-me"}]), encoding="utf-8"
    )

    report = migrate_legacy_workflows(agents_dir)

    assert len(report.migrated) == 2
    assert len(report.skipped_existing) == 1
    assert len(report.removed) == 3

    # Check migrated skills
    plain_skill = agents_dir / "skills" / "plain" / "SKILL.md"
    assert plain_skill.exists()
    plain_text = plain_skill.read_text(encoding="utf-8")
    assert "name: plain" in plain_text
    assert "description: Skill for Plain Flow." in plain_text
    assert "# Plain Flow" in plain_text

    no_desc_skill = agents_dir / "skills" / "no-desc" / "SKILL.md"
    assert no_desc_skill.exists()
    no_desc_text = no_desc_skill.read_text(encoding="utf-8")
    assert "name: no-desc" in no_desc_text
    assert "description: Custom skill migrated from no-desc." in no_desc_text

    # Check existing preserved
    assert existing_skill.read_text(encoding="utf-8") == "# Existing Skill Kept\n"

    # Check workflows directory is completely removed
    assert not workflows_dir.exists()

    # Check manifest cleanup (one kept item remains)
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data == [{"name": "keep-me"}]


def test_migrate_legacy_workflows_removes_empty_manifest(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".agents"
    workflows_dir = agents_dir / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "flow.md").write_text("# Flow\n", encoding="utf-8")
    manifest = agents_dir / "workflows.json"
    manifest.write_text(json.dumps([{"name": "flow"}]), encoding="utf-8")

    migrate_legacy_workflows(agents_dir)

    assert not workflows_dir.exists()
    assert not manifest.exists()


def test_migrate_legacy_workflows_noop_if_no_dir(tmp_path: Path) -> None:
    report = migrate_legacy_workflows(tmp_path / ".agents")
    assert len(report.migrated) == 0
    assert len(report.skipped_existing) == 0
    assert len(report.removed) == 0


def test_migrate_legacy_plan_skill_renames_dir_and_updates_frontmatter(
    tmp_path: Path,
) -> None:
    agents_dir = tmp_path / ".agents"
    legacy_dir = agents_dir / "skills" / "plan"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "SKILL.md").write_text(
        "---\nname: plan\ndescription: Legacy plan skill with /plan\n---\n# /plan\nContent here.\n",
        encoding="utf-8",
    )

    report = migrate_legacy_plan_skill(agents_dir, project_root=tmp_path)

    spec_plan_file = agents_dir / "skills" / "spec-plan" / "SKILL.md"
    assert spec_plan_file.exists()
    content = spec_plan_file.read_text(encoding="utf-8")
    assert "name: spec-plan" in content
    assert "Legacy plan skill with /spec-plan" in content
    assert "# /spec-plan\nContent here." in content
    assert not legacy_dir.exists()
    assert report.migrated_skill is True


def test_migrate_legacy_plan_skill_preserves_user_customizations(
    tmp_path: Path,
) -> None:
    agents_dir = tmp_path / ".agents"
    legacy_dir = agents_dir / "skills" / "plan"
    legacy_dir.mkdir(parents=True)
    custom_body = "# /plan\n- Step 1: Check Jira\n- Step 2: Write RFC\n"
    (legacy_dir / "SKILL.md").write_text(
        f"---\nname: plan\ndescription: Custom planner\n---\n{custom_body}",
        encoding="utf-8",
    )

    migrate_legacy_plan_skill(agents_dir, project_root=tmp_path)

    spec_plan_file = agents_dir / "skills" / "spec-plan" / "SKILL.md"
    assert spec_plan_file.exists()
    content = spec_plan_file.read_text(encoding="utf-8")
    assert "name: spec-plan" in content
    assert "# /spec-plan\n- Step 1: Check Jira\n- Step 2: Write RFC\n" in content
    assert not legacy_dir.exists()


def test_migrate_legacy_plan_skill_updates_references_without_breaking_quick_plan(
    tmp_path: Path,
) -> None:
    agents_dir = tmp_path / ".agents"
    rules_dir = agents_dir / "rules"
    rules_dir.mkdir(parents=True)
    (agents_dir / "skills" / "plan").mkdir(parents=True)
    (agents_dir / "skills" / "plan" / "SKILL.md").write_text(
        "---\nname: plan\n---\n# /plan\n", encoding="utf-8"
    )

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        "2. `/plan` — synthesize technical architecture\n"
        "Use `/quick-plan` for quick, non-SDD changes.\n",
        encoding="utf-8",
    )

    harness_core = rules_dir / "harness-core.md"
    harness_core.write_text(
        "A request should go through the `/plan` skill before any code is written.\n"
        "Use `/quick-plan` for lightweight work. When `/plan` or other harness work surfaces...\n",
        encoding="utf-8",
    )

    migrate_legacy_plan_skill(agents_dir, project_root=tmp_path)

    updated_agents = agents_md.read_text(encoding="utf-8")
    assert "`/spec-plan` — synthesize technical architecture" in updated_agents
    assert "`/quick-plan` for quick, non-SDD changes." in updated_agents
    assert "`/plan`" not in updated_agents

    updated_harness = harness_core.read_text(encoding="utf-8")
    assert "through the `/spec-plan` skill before" in updated_harness
    assert "When `/spec-plan` or other harness work surfaces" in updated_harness
    assert "`/quick-plan` for lightweight work" in updated_harness
    assert "`/plan`" not in updated_harness


def test_migrate_legacy_plan_skill_noop_when_no_legacy_plan(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True)

    report = migrate_legacy_plan_skill(agents_dir, project_root=tmp_path)
    assert report.migrated_skill is False
    assert report.removed_legacy_skill is False
    assert not (agents_dir / "skills" / "plan").exists()


def test_migrate_legacy_plan_skill_removes_legacy_if_target_already_exists(
    tmp_path: Path,
) -> None:
    agents_dir = tmp_path / ".agents"
    legacy_dir = agents_dir / "skills" / "plan"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "SKILL.md").write_text(
        "---\nname: plan\n---\n# /plan\n", encoding="utf-8"
    )

    spec_plan_dir = agents_dir / "skills" / "spec-plan"
    spec_plan_dir.mkdir(parents=True)
    (spec_plan_dir / "SKILL.md").write_text(
        "---\nname: spec-plan\n---\n# /spec-plan\n", encoding="utf-8"
    )

    report = migrate_legacy_plan_skill(agents_dir, project_root=tmp_path)
    assert report.removed_legacy_skill is True
    assert not legacy_dir.exists()
    assert spec_plan_dir.exists()
