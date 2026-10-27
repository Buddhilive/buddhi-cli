"""Generator for the two-layer DESIGN.md specification."""

from __future__ import annotations

import yaml

from buddhi.skills.design_md.models import DesignFacts

_DEFAULT_AESTHETIC = (
    "A graduate-level computer science lecture handout in the tradition of an old "
    "established university: restrained, typographic, high-contrast, editorial."
)


def generate_design_md(facts: DesignFacts, aesthetic: str | None = None) -> str:
    """Generate a spec-compliant two-layer DESIGN.md document."""
    aesthetic_prose = aesthetic or facts.aesthetic or _DEFAULT_AESTHETIC

    # Layer 1: Machine-Readable YAML Frontmatter
    frontmatter_dict = {
        "name": facts.name,
        "version": "1.0.0",
        "aesthetic": aesthetic_prose,
        "dials": {
            "energy": 1,
            "rhythm": 2,
            "motion": 1,
        },
        "colors": facts.tokens.colors,
        "typography": facts.tokens.typography,
        "spacing": facts.tokens.spacing,
        "rounded": facts.tokens.rounded,
        "elevation": facts.tokens.elevation,
    }

    yaml_block = yaml.safe_dump(
        frontmatter_dict,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )

    # Layer 2: Human-Readable Markdown Rationale (8 canonical sections)
    body_lines: list[str] = [
        f"# Design System: {facts.name}\n\n",
        "> This document defines the visual contracts, machine-readable design tokens, and human\n",
        "> rationale for this repository. AI coding agents and human engineers must adhere strictly\n",
        "> to these tokens and principles across all UI surfaces.\n\n",
        "## Overview\n\n",
        f"{aesthetic_prose}\n\n",
        "### Core Visual Principles\n",
        "- **Restraint Over Decoration**: Purposeful structure over decorative AI slop (no generic purple gradients, bento grids, or pill-everything).\n",
        "- **Unbroken Accessibility**: Minimum 4.5:1 contrast for normal text, visible `:focus-visible` rings, and native keyboard navigation.\n",
        "- **Semantic Intent**: High-intent interactive accents applied solely to active focal points, never as passive container fills.\n\n",
        "## Colors\n\n",
        "The palette uses semantic roles rather than arbitrary raw hex codes:\n\n",
        "| Role | Token Value | Purpose / Semantics |\n",
        "| :--- | :--- | :--- |\n",
    ]

    for k, v in facts.tokens.colors.items():
        purpose = "Semantic role"
        if "primary" in k:
            purpose = "Dominant heading, key call to action, active focal point"
        elif "background" in k:
            purpose = "Default page background canvas"
        elif "surface" in k:
            purpose = "Card, container, and elevated component background"
        elif "text-muted" in k or "muted" in k:
            purpose = "Secondary captions, metadata, supporting info"
        elif "text" in k:
            purpose = "Primary high-contrast reading text"
        elif "border" in k:
            purpose = "Structural component boundaries and dividers"
        elif "destructive" in k:
            purpose = "Destructive operations and danger states"
        body_lines.append(f"| `{k}` | `{v}` | {purpose} |\n")

    body_lines.extend(
        [
            "\n## Typography\n\n",
            "- **Type Hierarchy**: Clear typographic scale from `xs` through `2xl`.\n",
            "- **Line Length Limit**: Body prose constrained to max `65ch` for reading comfort.\n",
            "- **Weights**: Normal (400) for body, Medium (500) for interactive elements, Semibold/Bold (600/700) for section headings.\n\n",
            "## Layout\n\n",
            "- **Grid Foundation**: Strict multiples of 4px (`spacing.base`).\n",
            "- **Containers**: Responsive bounds (`sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`).\n",
            "- **Whitespace Rhythm**: Generous whitespace between semantic blocks, tight grouping within component fields.\n\n",
            "## Elevation & Depth\n\n",
            "- **Subtle Layering**: Flat architectural planes layered with crisp `1px` borders instead of excessive blurry drop shadows.\n",
            "- **Elevation Tiers**: Minimal shadows reserved for floating dialogs, dropdown popovers, and elevated modals.\n\n",
            "## Shapes\n\n",
            "- **Corner Geometry**: Consistent rounded corners (`rounded.md` for cards and buttons).\n",
            "- **Pill Ban**: Full pill borders (`rounded.full`) are reserved exclusively for tags, avatars, and chip badges.\n\n",
            "## Components\n\n",
            "### Buttons\n",
            "- **Primary**: 1 primary CTA per screen max. High-contrast solid brand fill.\n",
            "- **Secondary**: Subtle stroke/surface for supporting actions.\n",
            "- **Focus**: Unbroken `:focus-visible` ring (minimum 2px width with 2px offset).\n\n",
            "### Cards & Surfaces\n",
            "- Use semantic `<article>` or `<section>` tags; never create clickable `<div>` wrappers.\n",
            "- Structured with subtle `border.border` and `rounded.md`.\n\n",
            "### Inputs & Forms\n",
            "- Always pair `<label>` with `<input>` via matching `id`/`htmlFor`.\n",
            "- Minimum touch height 40–44px with visible `:focus-visible` states.\n\n",
            "## Do's and Don'ts\n\n",
            "| Do | Don't |\n",
            "| :--- | :--- |\n",
            "| Pull all colors, fonts, and radii directly from `DESIGN.md` tokens | Invent arbitrary hex colors, font sizes, or random margins |\n",
            "| Ensure all text meets WCAG 2.2 AA contrast ratios (>= 4.5:1) | Use light muted gray text on white backgrounds (< 4.5:1) |\n",
            "| Implement keyboard focus states with `:focus-visible` | Suppress focus rings with `outline: none` without replacement |\n",
            "| Use semantic HTML elements (`<button>`, `<main>`, `<nav>`) | Build interactive controls out of unstyled `<div>` or `<span>` |\n",
        ]
    )

    return f"---\n{yaml_block}---\n\n" + "".join(body_lines)
