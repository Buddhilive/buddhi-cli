---
name: repo-to-skill
description: Turn any GitHub repository or local directory into a tested, ready-to-use Google Antigravity agent skill. Analyzes documentation, examples, and entry points to generate Antigravity-compliant SKILL.md, references, and executable Python helper scripts.
---

# Repo-to-Skill Generator

Generate a complete, tested, and evaluated Google Antigravity agent skill from any GitHub repository or local codebase.

## Workflow Overview

```
Repository (URL or local) ➔ Analyze (buddhi skills run repo-to-skill) ➔ Classify ➔ Scaffold Antigravity Skill ➔ Test & Verify
```

Given a repository URL or local directory, this skill:
1. Analyzes the target codebase using `buddhi skills run repo-to-skill <target> --json`
2. Extracts usage patterns, public APIs, CLI flags, configuration, and dependencies
3. Generates an Antigravity-compliant skill (`SKILL.md` + `references/` + `scripts/`)
4. Verifies the generated skill with evaluation scenarios

---

## Step-by-Step Instructions

### Step 1: Analyze the Target Repository

Run the cross-platform repository analyzer via `buddhi-cli`:

```bash
buddhi skills run repo-to-skill <repo-url-or-path> --json
```

*(Alternatively: run `python .agents/skills/repo-to-skill/scripts/analyze_repo.py <repo-url-or-path> --json`)*

The analyzer extracts:
- **Project Type**: CLI tool, Python/TypeScript library, Web Framework, or Service/API
- **Primary Language & Entry Points**: CLI commands, package entrypoints, main modules
- **Key Dependencies & Prerequisites**: Installation method, environment variables
- **Public API & Core Operations**: The 5–10 most frequent usage workflows
- **Documentation Summary**: Key insights from README and docs directories

### Step 2: Classify the Tool

Determine the focus of the target skill based on the analyzer's output:

| Tool Classification | Skill Primary Focus | Common Examples |
| :--- | :--- | :--- |
| **CLI Tool** | Subcommands, options/flags, pipeline examples | `gh`, `ffmpeg`, `uv`, `docker` |
| **Code Library** | Public functions, classes, code snippets, typings | `pydantic`, `httpx`, `pandas` |
| **Framework** | Project structure, lifecycle hooks, idioms | `FastAPI`, `Next.js`, `Vite` |
| **Service / API** | Endpoints, authentication, request/response models | `Stripe`, `OpenAI`, `Supabase` |

### Step 3: Scaffold the Antigravity Skill

Create the skill in the workspace (`.agents/skills/<tool-name>/`) or global customizations root (`~/.gemini/config/skills/<tool-name>/`):

```text
<tool-name>/
├── SKILL.md                    # Core instructions with YAML frontmatter (< 500 lines)
├── references/                 # In-depth reference docs loaded on demand
│   ├── api-reference.md        # Detailed APIs or CLI arguments
│   └── examples.md             # Common and advanced usage examples
└── scripts/                    # Optional cross-platform Python scripts
    └── helper.py
```

#### Antigravity `SKILL.md` Standard Template

```markdown
---
name: <tool-name>
description: <Comprehensive description of what the tool does and when to activate this skill. Include trigger keywords and use cases.>
---

# <Tool Name>

> <One-line summary of capability>

## Overview & Installation

## Core Commands / Common Workflows

## Best Practices & Pitfalls

## References
- See [references/api-reference.md](references/api-reference.md) for full API options.
- See [references/examples.md](references/examples.md) for advanced use cases.
```

### Step 4: Verify and Test

1. Check that `SKILL.md` has valid YAML frontmatter (`name` and `description`).
2. Verify that all referenced scripts or reference markdown files exist.
3. Test any executable helper scripts using `run_command`.
