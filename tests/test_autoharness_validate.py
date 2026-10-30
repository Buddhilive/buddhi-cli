from __future__ import annotations

from pathlib import Path

from buddhi.scripts.autoharness.models import SkillIntent
from buddhi.scripts.autoharness.validate import (
    parse_frontmatter,
    validate_skill_candidate,
)


def test_parse_frontmatter_crlf_and_scalars() -> None:
    content = (
        "---\r\n"
        "name: git-commit-helper\r\n"
        "description: >-\r\n"
        "  Use when writing structured git commit messages.\r\n"
        "category: git\r\n"
        "---\r\n"
        "# Git Commit\r\n"
        "Follow conventional commits.\r\n"
    )
    fm, body = parse_frontmatter(content)
    assert fm["name"] == "git-commit-helper"
    assert "writing structured git commit messages" in fm["description"]
    assert fm["category"] == "git"
    assert "Follow conventional commits." in body


def test_gate_rejection_on_unredacted_secret(tmp_path: Path) -> None:
    body = (
        "---\n"
        "name: leaky-skill\n"
        "description: Use when connecting to AWS.\n"
        "category: general\n"
        "---\n"
        "Secret: AKIAIOSFODNN7EXAMPLE\n"
    )
    intent = SkillIntent(
        action="create",
        name="leaky-skill",
        body=body,
        reason="Test secret gate",
        evidence="Observed failure",
    )
    res = validate_skill_candidate(
        intent=intent,
        assembled_body=body,
        target_is_agent_created=False,
        target_exists=False,
        layer_root=tmp_path,
    )
    assert res.valid is False
    assert any(f.gate == "secrets" for f in res.findings)


def test_gate_rejection_on_safety_violation(tmp_path: Path) -> None:
    body = (
        "---\n"
        "name: dangerous-skill\n"
        "description: Use when cleaning root.\n"
        "category: general\n"
        "---\n"
        "rm -rf /\n"
    )
    intent = SkillIntent(
        action="create",
        name="dangerous-skill",
        body=body,
        reason="Test safety gate",
        evidence="Observed failure",
    )
    res = validate_skill_candidate(
        intent=intent,
        assembled_body=body,
        target_is_agent_created=False,
        target_exists=False,
        layer_root=tmp_path,
    )
    assert res.valid is False
    assert any(f.gate == "safety" for f in res.findings)
