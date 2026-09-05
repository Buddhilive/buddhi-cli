# Antigravity Skill Format Reference

A guide for formatting skills for Google Antigravity agents.

## Structure

```text
<skill-name>/
├── SKILL.md                 # Primary instruction file (MANDATORY)
├── references/              # Detailed documentation loaded on demand
│   ├── api-reference.md
│   └── examples.md
└── scripts/                 # Executable Python scripts
    └── helper.py
```

## Frontmatter Schema

Every `SKILL.md` MUST begin with a YAML frontmatter block containing:

```yaml
---
name: skill-name-in-kebab-case
description: Clear, action-oriented description of what the skill does and specific triggers/scenarios when an agent should load it.
---
```

## Guidelines

- Keep `SKILL.md` concise (< 500 lines) so it doesn't exhaust model context windows.
- Move extensive API documentation, configuration tables, or lengthy examples into `references/`.
- Use cross-platform Python scripts under `scripts/` instead of OS-specific shell scripts.
- Ensure scripts accept `--help` and output structured formats (such as `--json`) when applicable.
