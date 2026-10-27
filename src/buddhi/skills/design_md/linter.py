"""Structural and WCAG 2.2 AA contrast linter for DESIGN.md."""

from __future__ import annotations

import re
from typing import Any

import yaml

from buddhi.scripts.contrast import contrast_ratio, parse_color
from buddhi.skills.design_md.models import ContrastFinding, DesignLintReport

_CANONICAL_SECTIONS = [
    "overview",
    "colors",
    "typography",
    "layout",
    "elevation",
    "shapes",
    "components",
    "do's and don'ts",
]

_SEMANTIC_PAIRS = [
    ("text", "background", 4.5, False),
    ("text", "surface", 4.5, False),
    ("text-muted", "background", 4.5, True),
    ("text-muted", "surface", 4.5, True),
    ("primary-foreground", "primary", 4.5, False),
    ("secondary-foreground", "secondary", 4.5, False),
    ("accent-foreground", "accent", 4.5, False),
    ("border", "background", 3.0, False),
]


def lint_design_md(content: str) -> DesignLintReport:
    """Validate structure, sections, and evaluate WCAG 2.2 AA contrast ratios."""
    errors: list[str] = []
    warnings: list[str] = []
    missing_sections: list[str] = []
    contrast_findings: list[ContrastFinding] = []

    # 1. Frontmatter check
    has_frontmatter = content.startswith(("---\n", "---\r\n"))
    frontmatter_valid = False
    tokens_dict: dict[str, Any] = {}
    markdown_body = content

    if not has_frontmatter:
        errors.append(
            "DESIGN.md missing YAML frontmatter block ('---') at start of file."
        )
    else:
        parts = re.split(r"^---\r?\n", content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) >= 3:
            try:
                tokens_dict = yaml.safe_load(parts[1]) or {}
                frontmatter_valid = True
                markdown_body = parts[2]
            except yaml.YAMLError as exc:
                errors.append(f"Invalid YAML frontmatter: {exc}")
        else:
            errors.append("Unclosed YAML frontmatter block.")

    # 2. Check canonical Markdown sections
    headings = [
        m.group(1).lower().strip()
        for m in re.finditer(r"^#{1,3}\s+(.+)$", markdown_body, flags=re.MULTILINE)
    ]

    for canon in _CANONICAL_SECTIONS:
        matched = False
        for h in headings:
            if (
                canon in h
                or (canon == "elevation" and "depth" in h)
                or (canon == "do's and don'ts" and "dos" in h)
            ):
                matched = True
                break
        if not matched:
            missing_sections.append(canon)

    if missing_sections:
        errors.append(f"Missing canonical section(s): {', '.join(missing_sections)}")

    # 3. Check aesthetic prose presence in Overview
    if "aesthetic" not in tokens_dict or not tokens_dict.get("aesthetic"):
        warnings.append("Frontmatter missing 'aesthetic' vivid direction prose.")

    # 4. WCAG 2.2 AA Contrast Checks
    colors = tokens_dict.get("colors", {}) if isinstance(tokens_dict, dict) else {}
    if isinstance(colors, dict):
        for fg_key, bg_key, min_ratio, allow_large_fallback in _SEMANTIC_PAIRS:
            fg_val = colors.get(fg_key)
            bg_val = colors.get(bg_key)

            if not fg_val or not bg_val:
                continue

            try:
                fg_rgb = parse_color(fg_val)
                bg_rgb = parse_color(bg_val)
                ratio = contrast_ratio(fg_rgb, bg_rgb)
                passes_aa = ratio >= 4.5
                passes_large_aa = ratio >= 3.0

                if passes_aa or (allow_large_fallback and passes_large_aa):
                    status = "PASS"
                else:
                    status = "FAIL"
                    errors.append(
                        f"Contrast violation: '{fg_key}' ({fg_val}) on '{bg_key}' ({bg_val}) "
                        f"has ratio {ratio:.2f}:1, below required floor {min_ratio}:1."
                    )

                contrast_findings.append(
                    ContrastFinding(
                        fg_key=fg_key,
                        fg_hex=fg_val,
                        bg_key=bg_key,
                        bg_hex=bg_val,
                        ratio=round(ratio, 2),
                        passes_aa=passes_aa,
                        passes_large_aa=passes_large_aa,
                        status=status,
                    )
                )
            except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
                contrast_findings.append(
                    ContrastFinding(
                        fg_key=fg_key,
                        fg_hex=fg_val,
                        bg_key=bg_key,
                        bg_hex=bg_val,
                        ratio=0.0,
                        passes_aa=False,
                        passes_large_aa=False,
                        status="SKIPPED",
                        notes=f"Could not compute contrast: {exc}",
                    )
                )

    is_valid = len(errors) == 0
    return DesignLintReport(
        is_valid=is_valid,
        has_frontmatter=has_frontmatter,
        frontmatter_valid=frontmatter_valid,
        errors=errors,
        warnings=warnings,
        missing_sections=missing_sections,
        contrast_findings=contrast_findings,
    )
