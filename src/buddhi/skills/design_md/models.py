"""Data models for DESIGN.md design system codification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DesignTokens:
    """Structured design tokens corresponding to DESIGN.md YAML frontmatter."""

    colors: dict[str, str] = field(default_factory=dict)
    typography: dict[str, Any] = field(default_factory=dict)
    spacing: dict[str, Any] = field(default_factory=dict)
    rounded: dict[str, str] = field(default_factory=dict)
    elevation: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "colors": self.colors,
            "typography": self.typography,
            "spacing": self.spacing,
            "rounded": self.rounded,
            "elevation": self.elevation,
        }


@dataclass
class DesignFacts:
    """Discovered facts and extracted design tokens for a repository."""

    name: str
    aesthetic: str = ""
    has_ui_surface: bool = False
    framework: str | None = None
    source_files: list[str] = field(default_factory=list)
    tokens: DesignTokens = field(default_factory=DesignTokens)


@dataclass
class DesignSection:
    """A parsed Markdown section inside DESIGN.md."""

    heading: str
    level: int
    content: str
    is_managed: bool = False


@dataclass
class ContrastFinding:
    """Evaluation result for a foreground / background color token pair."""

    fg_key: str
    fg_hex: str
    bg_key: str
    bg_hex: str
    ratio: float
    passes_aa: bool
    passes_large_aa: bool
    status: str  # "PASS", "FAIL", or "SKIPPED"
    notes: str | None = None


@dataclass
class DesignLintReport:
    """Validation report for a DESIGN.md document."""

    is_valid: bool
    has_frontmatter: bool
    frontmatter_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    contrast_findings: list[ContrastFinding] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of merging new facts into an existing DESIGN.md."""

    content: str
    diff: str
    has_changes: bool
    updated_sections: list[str] = field(default_factory=list)
    preserved_sections: list[str] = field(default_factory=list)
