"""Tests for the DESIGN.md skill and Python engine."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from buddhi.skills.design_md.detector import detect_design_facts
from buddhi.skills.design_md.generator import generate_design_md
from buddhi.skills.design_md.linter import lint_design_md
from buddhi.skills.design_md.merger import merge_design_md


@pytest.fixture
def sample_css_project(tmp_path: Path) -> Path:
    """Fixture creating a project with CSS custom properties."""
    css_dir = tmp_path / "styles"
    css_dir.mkdir(parents=True)
    css_file = css_dir / "globals.css"
    css_file.write_text(
        """
:root {
  --color-primary: #1e293b;
  --color-primary-foreground: #ffffff;
  --color-background: #ffffff;
  --color-surface: #f8fafc;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-border: #e2e8f0;
  --font-sans: "Inter, sans-serif";
  --font-mono: "JetBrains Mono, monospace";
  --spacing-base: 4px;
  --radius-md: 6px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def sample_tailwind_project(tmp_path: Path) -> Path:
    """Fixture creating a project with tailwind.config.js."""
    tw_file = tmp_path / "tailwind.config.js"
    tw_file.write_text(
        """
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: "#2563eb",
        surface: "#0f172a",
        text: "#f8fafc",
      },
      fontFamily: {
        sans: ["Public Sans", "sans-serif"],
      },
      borderRadius: {
        md: "8px",
      }
    }
  }
}
""",
        encoding="utf-8",
    )
    return tmp_path


def test_detect_facts_css_variables(sample_css_project: Path) -> None:
    facts = detect_design_facts(sample_css_project)
    assert facts.has_ui_surface is True
    assert facts.tokens.colors.get("primary") == "#1e293b"
    assert facts.tokens.colors.get("background") == "#ffffff"
    assert facts.tokens.colors.get("text") == "#0f172a"
    assert "Inter, sans-serif" in str(facts.tokens.typography)
    assert facts.tokens.rounded.get("md") == "6px"


def test_detect_facts_tailwind_config(sample_tailwind_project: Path) -> None:
    facts = detect_design_facts(sample_tailwind_project)
    assert facts.has_ui_surface is True
    assert facts.tokens.colors.get("primary") == "#2563eb"
    assert facts.tokens.colors.get("surface") == "#0f172a"
    assert facts.tokens.rounded.get("md") == "8px"


def test_detect_facts_no_ui_fallback(tmp_path: Path) -> None:
    facts = detect_design_facts(tmp_path)
    assert facts.has_ui_surface is False
    assert "primary" in facts.tokens.colors
    assert "background" in facts.tokens.colors
    assert "sans" in facts.tokens.typography.get("fonts", {})


def test_generate_two_layer_design_md(sample_css_project: Path) -> None:
    facts = detect_design_facts(sample_css_project)
    content = generate_design_md(
        facts,
        aesthetic="A graduate-level computer science lecture handout in the tradition of an old established university.",
    )
    assert content.startswith("---\n")
    # Verify YAML frontmatter parses cleanly
    parts = content.split("---\n", 2)
    assert len(parts) >= 3
    fm = yaml.safe_load(parts[1])
    assert fm["name"] == sample_css_project.name
    assert "lecture handout" in fm["aesthetic"]
    assert "colors" in fm
    assert "typography" in fm

    # Verify 8 canonical Markdown sections
    body = parts[2]
    canonical_sections = [
        "## Overview",
        "## Colors",
        "## Typography",
        "## Layout",
        "## Elevation & Depth",
        "## Shapes",
        "## Components",
        "## Do's and Don'ts",
    ]
    for sec in canonical_sections:
        assert sec in body, f"Missing section: {sec}"


def test_merge_preserves_custom_prose(tmp_path: Path) -> None:
    initial_facts = detect_design_facts(tmp_path)
    initial_content = generate_design_md(
        initial_facts,
        aesthetic="A graduate-level computer science lecture handout in the tradition of an old established university.",
    )
    # Add custom hand-written section and custom overview text
    custom_content = initial_content.replace(
        "## Overview",
        "## Overview\nThis is unique hand-written design prose that must never be wiped.\n",
    )
    custom_content += (
        "\n## Brand Voice\nAlways speaks with dry wit and academic precision.\n"
    )

    # Merge updated facts
    updated_facts = detect_design_facts(tmp_path)
    updated_facts.tokens.colors["accent"] = "#f59e0b"

    res = merge_design_md(custom_content, updated_facts)
    assert "unique hand-written design prose" in res.content
    assert "## Brand Voice" in res.content
    assert "Always speaks with dry wit and academic precision" in res.content
    assert "## Brand Voice" in res.preserved_sections


def test_linter_wcag_contrast_pass_and_fail(tmp_path: Path) -> None:
    # 1. Compliant content (black text on white surface -> ratio 21:1)
    good_facts = detect_design_facts(tmp_path)
    good_facts.tokens.colors = {
        "background": "#ffffff",
        "surface": "#ffffff",
        "text": "#000000",
        "primary": "#000000",
        "primary-foreground": "#ffffff",
    }
    good_md = generate_design_md(good_facts)
    report = lint_design_md(good_md)
    assert report.is_valid is True
    assert len(report.errors) == 0

    # 2. Failing contrast (light grey text on white surface -> ratio < 4.5:1)
    bad_facts = detect_design_facts(tmp_path)
    bad_facts.tokens.colors = {
        "background": "#ffffff",
        "surface": "#ffffff",
        "text": "#cccccc",
        "primary": "#cccccc",
        "primary-foreground": "#ffffff",
    }
    bad_md = generate_design_md(bad_facts)
    bad_report = lint_design_md(bad_md)
    assert bad_report.is_valid is False
    failing_pairs = [f for f in bad_report.contrast_findings if f.status == "FAIL"]
    assert len(failing_pairs) > 0


def test_init_scaffolds_design_md_skill_idempotent(tmp_path: Path) -> None:
    from buddhi.commands.init import init

    # 1. Run init on clean directory
    init(path=tmp_path)
    skill_file = tmp_path / ".agents" / "skills" / "design-md" / "SKILL.md"
    script_file = (
        tmp_path
        / ".agents"
        / "skills"
        / "design-md"
        / "scripts"
        / "detect_design_md.py"
    )
    ref_file = (
        tmp_path
        / ".agents"
        / "skills"
        / "design-md"
        / "references"
        / "design-md-spec.md"
    )

    assert skill_file.is_file()
    assert script_file.is_file()
    assert ref_file.is_file()

    # 2. Modify skill file with custom instruction
    custom_content = skill_file.read_text(encoding="utf-8") + "\n# Custom User Note\n"
    skill_file.write_text(custom_content, encoding="utf-8")

    # 3. Rerun init and verify idempotency (customization preserved)
    init(path=tmp_path)
    assert skill_file.read_text(encoding="utf-8") == custom_content
