"""Concise AGENTS.md markdown generator."""

from __future__ import annotations

from buddhi.skills.agents_md.models import RepoFacts


def generate_agents_md(facts: RepoFacts) -> str:
    """Generate a concise, ~12-15 line AGENTS.md core block."""
    lines: list[str] = [
        "# AGENTS.md",
        "",
    ]

    desc = facts.description.strip() if facts.description else f"{facts.name} codebase"
    if not desc.endswith("."):
        desc += "."
    lines.append(f"> {facts.name} - {desc}")
    lines.append("")

    lines.append("## Commands")
    cmds = facts.commands

    if cmds.install:
        lines.append(f"- **Install**: `{cmds.install}`")
    if cmds.build:
        lines.append(f"- **Build**: `{cmds.build}`")
    if cmds.test:
        lines.append(f"- **Test**: `{cmds.test}`")
    if cmds.lint:
        lines.append(f"- **Lint & Format**: `{cmds.lint}`")
    if cmds.typecheck:
        lines.append(f"- **Typecheck**: `{cmds.typecheck}`")

    # If no commands were detected at all
    if not any([cmds.install, cmds.build, cmds.test, cmds.lint, cmds.typecheck]):
        lines.append("- *(No standard build or test commands detected in manifests)*")

    lines.append("")
    lines.append("## Agent Conventions & Skills")
    lines.append(
        "- Consult `.agents/skills/` for granular workflows and `.agents/rules/` for codebase constraints."
    )
    if facts.has_buddhi_docs:
        lines.append(
            "- Consult `.buddhi/docs/` for code graph and symbol documentation."
        )
    else:
        lines.append(
            "- Consult `.buddhi/docs/` for code graph and symbol documentation (run `buddhi generate`)."
        )

    return "\n".join(lines) + "\n"
