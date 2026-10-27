"""Non-destructive section-aware merger and diff generator for DESIGN.md."""

from __future__ import annotations

import difflib
import re
from typing import Any

import yaml

from buddhi.skills.design_md.models import DesignFacts, DesignSection, MergeResult

_MANAGED_HEADINGS = {
    "overview",
    "colors",
    "typography",
    "layout",
    "elevation & depth",
    "elevation",
    "shapes",
    "components",
    "do's and don'ts",
    "dos and don'ts",
}


def parse_design_sections(markdown_body: str) -> list[DesignSection]:
    """Parse Markdown content into structured sections based on H1-H3 headers."""
    lines = markdown_body.splitlines(keepends=True)
    sections: list[DesignSection] = []

    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    header_re = re.compile(r"^(#{1,3})\s+(.*)$")

    for line in lines:
        match = header_re.match(line.rstrip("\r\n"))
        if match:
            if current_heading or current_lines:
                norm_h = current_heading.lstrip("#").strip().lower()
                is_managed = norm_h in _MANAGED_HEADINGS or norm_h.startswith(
                    "design system"
                )
                sections.append(
                    DesignSection(
                        heading=current_heading,
                        level=current_level,
                        content="".join(current_lines),
                        is_managed=is_managed,
                    )
                )
            current_heading = line.strip()
            current_level = len(match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading or current_lines:
        norm_h = current_heading.lstrip("#").strip().lower()
        is_managed = norm_h in _MANAGED_HEADINGS or norm_h.startswith("design system")
        sections.append(
            DesignSection(
                heading=current_heading,
                level=current_level,
                content="".join(current_lines),
                is_managed=is_managed,
            )
        )

    return sections


def diff_design_md(old_content: str, new_content: str) -> str:
    """Generate a clean unified diff between old and new DESIGN.md content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_gen = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="a/DESIGN.md",
        tofile="b/DESIGN.md",
    )
    return "".join(diff_gen)


def merge_design_md(
    existing_content: str,
    facts: DesignFacts,
    aesthetic: str | None = None,
) -> MergeResult:
    """Merge newly detected facts into an existing DESIGN.md.

    Preserves hand-crafted aesthetic prose and custom user sections byte-for-byte.
    """
    from buddhi.skills.design_md.generator import generate_design_md

    if not existing_content.strip():
        new_content = generate_design_md(facts, aesthetic=aesthetic)
        diff_str = diff_design_md(existing_content, new_content)
        return MergeResult(
            content=new_content,
            diff=diff_str,
            has_changes=bool(diff_str),
            updated_sections=["All sections (new file)"],
            preserved_sections=[],
        )

    # 1. Split existing frontmatter from Markdown body
    existing_fm: dict[str, Any] = {}
    markdown_body = existing_content
    if existing_content.startswith(("---\n", "---\r\n")):
        parts = re.split(r"^---\r?\n", existing_content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) >= 3:
            try:
                existing_fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                existing_fm = {}
            markdown_body = parts[2]

    # 2. Update frontmatter tokens while preserving custom metadata & aesthetic
    merged_aesthetic = (
        aesthetic
        or existing_fm.get("aesthetic")
        or facts.aesthetic
        or "A graduate-level computer science lecture handout in the tradition of an old established university."
    )
    frontmatter_dict = dict(existing_fm)
    frontmatter_dict["name"] = existing_fm.get("name") or facts.name
    frontmatter_dict["version"] = existing_fm.get("version") or "1.0.0"
    frontmatter_dict["aesthetic"] = merged_aesthetic
    frontmatter_dict["colors"] = {
        **facts.tokens.colors,
        **existing_fm.get("colors", {}),
    }
    frontmatter_dict["typography"] = {
        **facts.tokens.typography,
        **existing_fm.get("typography", {}),
    }
    frontmatter_dict["spacing"] = {
        **facts.tokens.spacing,
        **existing_fm.get("spacing", {}),
    }
    frontmatter_dict["rounded"] = {
        **facts.tokens.rounded,
        **existing_fm.get("rounded", {}),
    }
    frontmatter_dict["elevation"] = {
        **facts.tokens.elevation,
        **existing_fm.get("elevation", {}),
    }

    yaml_block = yaml.safe_dump(
        frontmatter_dict,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )

    # 3. Parse Markdown sections
    sections = parse_design_sections(markdown_body)
    updated_sections: list[str] = ["Frontmatter"]
    preserved_sections: list[str] = []
    out_parts: list[str] = []

    for sec in sections:
        norm_h = sec.heading.lstrip("#").strip().lower()

        if norm_h in _MANAGED_HEADINGS or norm_h.startswith("design system"):
            # If user explicitly supplied new aesthetic prose and this is ## Overview, update it
            if norm_h == "overview" and aesthetic:
                out_parts.append(sec.heading + "\n\n")
                out_parts.append(aesthetic.strip() + "\n\n")
                updated_sections.append(sec.heading)
            else:
                # Managed section with existing user prose: PRESERVE PROSE
                out_parts.append(sec.heading + "\n")
                out_parts.append(sec.content)
                preserved_sections.append(sec.heading)
        else:
            # Unmanaged custom user section: PRESERVE 100% BYTE-FOR-BYTE
            out_parts.append(sec.heading + "\n")
            out_parts.append(sec.content)
            preserved_sections.append(sec.heading)

    merged_content = f"---\n{yaml_block}---\n\n" + "".join(out_parts)
    if not merged_content.endswith("\n"):
        merged_content += "\n"

    diff_str = diff_design_md(existing_content, merged_content)

    return MergeResult(
        content=merged_content,
        diff=diff_str,
        has_changes=bool(diff_str),
        updated_sections=updated_sections,
        preserved_sections=preserved_sections,
    )
