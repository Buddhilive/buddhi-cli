"""agents_md package for repository facts detection and AGENTS.md generation/merging."""

from __future__ import annotations

from buddhi.skills.agents_md.detector import detect_repo_facts
from buddhi.skills.agents_md.generator import generate_agents_md
from buddhi.skills.agents_md.models import (
    AgentsSection,
    CommandSet,
    MergeResult,
    RepoFacts,
)

__all__ = [
    "AgentsSection",
    "CommandSet",
    "MergeResult",
    "RepoFacts",
    "detect_repo_facts",
    "diff_agents_md",
    "generate_agents_md",
    "merge_agents_md",
    "parse_agents_sections",
]


def parse_agents_sections(content: str) -> list[AgentsSection]:
    from buddhi.skills.agents_md.merger import parse_agents_sections as _parse

    return _parse(content)


def merge_agents_md(existing_content: str, facts: RepoFacts) -> MergeResult:
    from buddhi.skills.agents_md.merger import merge_agents_md as _merge

    return _merge(existing_content, facts)


def diff_agents_md(old_content: str, new_content: str) -> str:
    from buddhi.skills.agents_md.merger import diff_agents_md as _diff

    return _diff(old_content, new_content)
