"""Data models for agents-md repository facts detection and merge engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommandSet:
    """Core development and verification commands detected in a repository."""

    install: str | None = None
    build: str | None = None
    test: str | None = None
    lint: str | None = None
    typecheck: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "install": self.install,
            "build": self.build,
            "test": self.test,
            "lint": self.lint,
            "typecheck": self.typecheck,
        }


@dataclass
class RepoFacts:
    """Repository characteristics detected from manifests and structure."""

    name: str
    description: str = ""
    commands: CommandSet = field(default_factory=CommandSet)
    primary_language: str = "unknown"
    skills: list[str] = field(default_factory=list)
    has_skills: bool = False
    has_rules: bool = False
    has_buddhi_docs: bool = False


@dataclass
class AgentsSection:
    """A section of an AGENTS.md document split by Markdown headers."""

    heading: str
    level: int
    content: str
    is_managed: bool = False


@dataclass
class MergeResult:
    """Result of merging detected repo facts into an existing AGENTS.md."""

    content: str
    diff: str
    has_changes: bool
    updated_sections: list[str] = field(default_factory=list)
    preserved_sections: list[str] = field(default_factory=list)
