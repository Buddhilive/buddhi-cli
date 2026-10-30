"""Tests for agents-md skill: detection, generation, and safe merging."""

from __future__ import annotations

from pathlib import Path

from buddhi.skills.agents_md import (
    CommandSet,
    RepoFacts,
    detect_repo_facts,
    generate_agents_md,
    merge_agents_md,
    parse_agents_sections,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "agents_md"


# ---------------------------------------------------------------------------
# US1: Detection and Generation (P1 MVP)
# ---------------------------------------------------------------------------


def test_detect_python_uv() -> None:
    repo_dir = FIXTURES_DIR / "python_uv"
    facts = detect_repo_facts(repo_dir)

    assert facts.name == "sample-uv-app"
    assert "sample python uv" in facts.description.lower()
    assert facts.primary_language == "python"
    assert facts.commands.install == "uv sync"
    assert facts.commands.test == "uv run pytest"
    assert "ruff" in (facts.commands.lint or "")
    assert "mypy" in (facts.commands.typecheck or "")


def test_detect_python_poetry() -> None:
    repo_dir = FIXTURES_DIR / "python_poetry"
    facts = detect_repo_facts(repo_dir)

    assert facts.name == "sample-poetry-app"
    assert facts.primary_language == "python"
    assert facts.commands.install == "poetry install"
    assert facts.commands.test == "poetry run pytest"


def test_detect_node_pnpm() -> None:
    repo_dir = FIXTURES_DIR / "node_pnpm"
    facts = detect_repo_facts(repo_dir)

    assert facts.name == "sample-node-app"
    assert facts.primary_language in ("javascript", "typescript")
    assert facts.commands.install == "pnpm install"
    assert facts.commands.build == "pnpm run build"
    assert facts.commands.test == "pnpm run test"
    assert facts.commands.lint == "pnpm run lint"
    assert facts.commands.typecheck == "pnpm run typecheck"


def test_detect_rust_cargo() -> None:
    repo_dir = FIXTURES_DIR / "rust_cargo"
    facts = detect_repo_facts(repo_dir)

    assert facts.name == "sample-rust-cli"
    assert facts.primary_language == "rust"
    assert facts.commands.build == "cargo build"
    assert facts.commands.test == "cargo test"


def test_detect_go_mod() -> None:
    repo_dir = FIXTURES_DIR / "go_mod"
    facts = detect_repo_facts(repo_dir)

    assert facts.name == "sample-go-service"
    assert facts.primary_language == "go"
    assert facts.commands.install == "go mod download"
    assert facts.commands.test == "go test ./..."


def test_detect_makefile() -> None:
    repo_dir = FIXTURES_DIR / "makefile_project"
    facts = detect_repo_facts(repo_dir)

    assert facts.commands.build == "make build"
    assert facts.commands.test == "make test"
    assert facts.commands.lint == "make lint"


def test_generate_concise_budget() -> None:
    facts = RepoFacts(
        name="test-project",
        description="A lightweight testing utility.",
        primary_language="python",
        commands=CommandSet(
            install="uv sync",
            build="uv build",
            test="uv run pytest",
            lint="uv run ruff check .",
            typecheck="uv run mypy src/",
        ),
        has_skills=True,
        has_rules=True,
        has_buddhi_docs=True,
    )

    content = generate_agents_md(facts)
    lines = content.strip().splitlines()

    # Brevity check: core block must be ~12-15 lines
    assert 10 <= len(lines) <= 16, (
        f"Expected 10-16 lines, got {len(lines)} lines:\n{content}"
    )
    assert "# AGENTS.md" in content
    assert "## Commands" in content
    assert "- **Install**: `uv sync`" in content
    assert "- **Test**: `uv run pytest`" in content
    assert ".agents/skills/" in content
    assert ".agents/rules/" in content
    assert ".buddhi/docs/" in content


# ---------------------------------------------------------------------------
# US2: Section-Aware Parsing, Custom Section Preservation, Diffing (P2)
# ---------------------------------------------------------------------------


def test_parse_agents_sections() -> None:
    sample = (
        "# AGENTS.md\n\n"
        "> Sample overview.\n\n"
        "## Commands\n"
        "- **Install**: `pip install -e .`\n\n"
        "## Custom Section\n"
        "- Keep this text verbatim.\n"
    )

    sections = parse_agents_sections(sample)
    assert len(sections) == 3
    assert sections[0].heading == "# AGENTS.md"
    assert sections[1].heading == "## Commands"
    assert sections[2].heading == "## Custom Section"
    assert "Keep this text verbatim" in sections[2].content


def test_merge_preserves_custom_sections_byte_identical() -> None:
    custom_body = (
        "- Do not touch production database without confirmation.\n"
        "- Keep cognitive complexity bounded under 15.\n\n"
        "### Sub-heading Detail\n"
        "1. Never bypass guard checks.\n"
    )
    existing = (
        "# AGENTS.md\n\n"
        "> My Old Project - Old description.\n\n"
        "## Commands\n"
        "- **Install**: `pip install -r requirements.txt`\n"
        "- **Test**: `pytest`\n\n"
        "## Engineering Principles & Non-Negotiables\n"
        f"{custom_body}\n"
        "## Agent Conventions & Skills\n"
        "- Consult `.agents/skills/`\n"
    )

    new_facts = RepoFacts(
        name="My Modern Project",
        description="Updated description with uv.",
        primary_language="python",
        commands=CommandSet(
            install="uv sync",
            test="uv run pytest",
            lint="uv run ruff check .",
        ),
        has_buddhi_docs=True,
    )

    result = merge_agents_md(existing, new_facts)

    assert result.has_changes is True
    assert "uv sync" in result.content
    assert "uv run pytest" in result.content
    assert "uv run ruff check ." in result.content

    # The custom section must be preserved exactly byte-identical
    assert custom_body in result.content
    assert "## Engineering Principles & Non-Negotiables" in result.content

    # Diff must be non-empty and formatted as unified diff
    assert result.diff != ""
    assert "--- a/AGENTS.md" in result.diff
    assert "+++ b/AGENTS.md" in result.diff
    assert "+- **Install**: `uv sync`" in result.diff


def test_merge_idempotent() -> None:
    facts = RepoFacts(
        name="Stable App",
        description="A stable application.",
        commands=CommandSet(install="uv sync", test="uv run pytest"),
        has_buddhi_docs=True,
    )
    initial = generate_agents_md(facts)
    result = merge_agents_md(initial, facts)

    assert result.has_changes is False
    assert result.diff == ""
    assert result.content == initial


# ---------------------------------------------------------------------------
# US3: Antigravity Skill and Default Init Scaffolding (P3)
# ---------------------------------------------------------------------------


def test_agents_md_not_in_custom_skills_registry() -> None:
    """Verify agents-md is not in optional custom skills (it is a default skill)."""
    from buddhi.skills.registry import get_skill, list_skills

    assert get_skill("agents-md") is None
    skills = list_skills()
    assert not any(s.name == "agents-md" for s in skills)


def test_agents_md_default_init_template() -> None:
    """Verify agents-md template is present in default init skills tree."""
    template_skill = Path("src/buddhi/templates/agents/skills/agents-md")
    assert (template_skill / "SKILL.md").is_file()
    assert (template_skill / "scripts" / "detect_agents_md.py").is_file()

    # Verify SKILL.md frontmatter
    skill_content = (template_skill / "SKILL.md").read_text(encoding="utf-8")
    assert "name: agents-md" in skill_content
    assert "description:" in skill_content


def test_detect_agents_md_script_execution() -> None:
    """Verify detect_agents_md.py helper script executes properly."""
    import subprocess
    import sys

    script = Path(".agents/skills/agents-md/scripts/detect_agents_md.py")
    assert script.is_file()

    # Run with --json on this repository
    res = subprocess.run(
        [sys.executable, str(script), "--json", "--root", "."],
        capture_output=True,
        text=True,
        check=True,
    )
    assert '"commands"' in res.stdout
    assert "pytest" in res.stdout
