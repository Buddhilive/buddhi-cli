"""Section-aware parser, merger, and diff generator for AGENTS.md."""

from __future__ import annotations

import difflib
import re

from buddhi.skills.agents_md.models import AgentsSection, MergeResult, RepoFacts

_MANAGED_HEADINGS = {
    "commands",
    "agent conventions & skills",
    "agent conventions",
    "skills & architecture",
    "overview",
}


def parse_agents_sections(content: str) -> list[AgentsSection]:
    """Parse an AGENTS.md markdown string into structured sections."""
    lines = content.splitlines(keepends=True)
    sections: list[AgentsSection] = []

    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    header_re = re.compile(r"^(#{1,6})\s+(.*)$")

    for line in lines:
        match = header_re.match(line.rstrip("\r\n"))
        # Only split on level 1 or level 2 headers for major sections
        if match and len(match.group(1)) <= 2:
            if current_heading or current_lines:
                norm_h = current_heading.lstrip("#").strip().lower()
                is_managed = norm_h in _MANAGED_HEADINGS or norm_h.startswith(
                    "agents.md"
                )
                sections.append(
                    AgentsSection(
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
        is_managed = norm_h in _MANAGED_HEADINGS or norm_h.startswith("agents.md")
        sections.append(
            AgentsSection(
                heading=current_heading,
                level=current_level,
                content="".join(current_lines),
                is_managed=is_managed,
            )
        )

    return sections


def _build_commands_body(facts: RepoFacts) -> str:
    """Format the body of ## Commands section."""
    lines: list[str] = []
    cmds = facts.commands

    if cmds.install:
        lines.append(f"- **Install**: `{cmds.install}`\n")
    if cmds.build:
        lines.append(f"- **Build**: `{cmds.build}`\n")
    if cmds.test:
        lines.append(f"- **Test**: `{cmds.test}`\n")
    if cmds.lint:
        lines.append(f"- **Lint & Format**: `{cmds.lint}`\n")
    if cmds.typecheck:
        lines.append(f"- **Typecheck**: `{cmds.typecheck}`\n")

    if not any([cmds.install, cmds.build, cmds.test, cmds.lint, cmds.typecheck]):
        lines.append("- *(No standard build or test commands detected)*\n")

    lines.append("\n")
    return "".join(lines)


def _build_conventions_body(facts: RepoFacts) -> str:
    """Format the body of ## Agent Conventions & Skills section."""
    lines: list[str] = [
        "- Consult `.agents/skills/` for granular workflows and `.agents/rules/` for codebase constraints.\n",
    ]
    if facts.has_buddhi_docs:
        lines.append(
            "- Consult `.buddhi/docs/` for code graph and symbol documentation.\n"
        )
    else:
        lines.append(
            "- Consult `.buddhi/docs/` for code graph and symbol documentation (run `buddhi generate`).\n"
        )
    return "".join(lines)


def diff_agents_md(old_content: str, new_content: str) -> str:
    """Generate a clean unified diff between old and new AGENTS.md content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_gen = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="a/AGENTS.md",
        tofile="b/AGENTS.md",
    )
    return "".join(diff_gen)


def merge_agents_md(existing_content: str, facts: RepoFacts) -> MergeResult:
    """Safely merge newly detected repo facts into an existing AGENTS.md.

    Preserves all unmanaged custom user sections byte-for-byte in their original order.
    """
    sections = parse_agents_sections(existing_content)
    if not sections:
        # File is empty, generate from scratch
        from buddhi.skills.agents_md.generator import generate_agents_md

        new_content = generate_agents_md(facts)
        diff_str = diff_agents_md(existing_content, new_content)
        return MergeResult(
            content=new_content,
            diff=diff_str,
            has_changes=bool(diff_str),
            updated_sections=[
                "# AGENTS.md",
                "## Commands",
                "## Agent Conventions & Skills",
            ],
        )

    updated_sections: list[str] = []
    preserved_sections: list[str] = []
    out_parts: list[str] = []

    has_seen_commands = False
    has_seen_conventions = False

    for sec in sections:
        norm_h = sec.heading.lstrip("#").strip().lower()

        if norm_h.startswith("agents.md") or sec.level == 1:
            # Top-level title and description blockquote
            out_parts.append(sec.heading + "\n")
            # If the user has a custom blockquote, preserve or update smoothly
            if facts.description and ">" in sec.content:
                # Update blockquote line while keeping surrounding layout
                desc = facts.description.strip()
                if not desc.endswith("."):
                    desc += "."
                new_body_lines: list[str] = []
                for line in sec.content.splitlines(keepends=True):
                    if line.strip().startswith(">"):
                        new_body_lines.append(f"> {facts.name} - {desc}\n")
                    else:
                        new_body_lines.append(line)
                out_parts.append("".join(new_body_lines))
            else:
                out_parts.append(sec.content)
            updated_sections.append(sec.heading)

        elif norm_h == "commands":
            has_seen_commands = True
            out_parts.append(sec.heading + "\n")
            out_parts.append(_build_commands_body(facts))
            updated_sections.append(sec.heading)

        elif norm_h in (
            "agent conventions & skills",
            "agent conventions",
            "skills & architecture",
        ):
            has_seen_conventions = True
            out_parts.append(sec.heading + "\n")
            out_parts.append(_build_conventions_body(facts))
            updated_sections.append(sec.heading)

        else:
            # Unmanaged custom section: PRESERVE VERBATIM
            out_parts.append(sec.heading + "\n")
            out_parts.append(sec.content)
            preserved_sections.append(sec.heading)

    # If Commands or Conventions were not present in existing file, append them
    if not has_seen_commands:
        out_parts.append("\n## Commands\n")
        out_parts.append(_build_commands_body(facts))
        updated_sections.append("## Commands")

    if not has_seen_conventions:
        out_parts.append("\n## Agent Conventions & Skills\n")
        out_parts.append(_build_conventions_body(facts))
        updated_sections.append("## Agent Conventions & Skills")

    merged_content = "".join(out_parts)
    # Normalize ending with single newline
    if not merged_content.endswith("\n"):
        merged_content += "\n"

    diff_str = diff_agents_md(existing_content, merged_content)

    return MergeResult(
        content=merged_content,
        diff=diff_str,
        has_changes=bool(diff_str),
        updated_sections=updated_sections,
        preserved_sections=preserved_sections,
    )
