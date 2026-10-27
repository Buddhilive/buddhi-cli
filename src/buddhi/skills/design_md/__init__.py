"""DESIGN.md skill: design system codification for Google Antigravity."""

from __future__ import annotations

from buddhi.skills.design_md.detector import detect_design_facts
from buddhi.skills.design_md.generator import generate_design_md
from buddhi.skills.design_md.linter import lint_design_md
from buddhi.skills.design_md.merger import diff_design_md, merge_design_md
from buddhi.skills.design_md.models import (
    ContrastFinding,
    DesignFacts,
    DesignLintReport,
    DesignSection,
    DesignTokens,
    MergeResult,
)

__all__ = [
    "ContrastFinding",
    "DesignFacts",
    "DesignLintReport",
    "DesignSection",
    "DesignTokens",
    "MergeResult",
    "detect_design_facts",
    "diff_design_md",
    "generate_design_md",
    "lint_design_md",
    "merge_design_md",
]
