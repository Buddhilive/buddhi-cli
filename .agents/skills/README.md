# Antigravity Skills in Buddhi

This directory holds Google Antigravity skills (`.agents/skills/<name>/SKILL.md`).
Antigravity automatically discovers every `SKILL.md` in this directory:
- **Slash Commands**: You can explicitly invoke any skill by typing `/<skill-name>` in the chat prompt (e.g. `/specify`, `/spec-plan`, `/spec-tasks`, `/implement`, `/verify`, `/ask`, `/quick-plan`, `/document-codebase`, `/debug`, `/remember`, `/status`).
- **Autonomous Discovery**: The agent evaluates the YAML frontmatter `description` of each skill against the active conversation and activates it when relevant.

## Core Buddhi Skills

1. **Spec-Driven Development (SDD)**:
   - `specify`: Feature specification scaffolding and refinement (`/specify`).
   - `spec-plan`: Multi-specialist architectural planning (`/spec-plan`).
   - `spec-tasks`: Actionable user-story task breakdown (`/spec-tasks`).
   - `implement`: Step-by-step task execution with checkpoints (`/implement`).
   - `verify`: Real test execution and SDD acceptance convergence (`/verify`).
2. **Architecture & Exploration**:
   - `ask`: Topological code-graph and OKF doc question answering (`/ask`).
   - `quick-plan`: Lightweight planning for non-SDD changes (`/quick-plan`).
   - `debug`: Systematic root-cause investigation without code changes (`/debug`).
   - `status`: Health and state dashboard for docs, graph, plans, and git (`/status`).
3. **Knowledge & Documentation**:
   - `okf-context`: Primary code-reading discipline using Buddhi MCP tools and OKF docs.
   - `document-codebase`: Bottom-up OKF doc generation command (`/document-codebase`).
   - `repoagent-doc-generation`: Topological per-symbol documentation engine.
   - `system-design`: Principled trade-off evaluations for structural choices.
   - `remember`: Explicit cross-session memory capture (`/remember`).

## Adding Custom or Tech-Stack Skills

To add tech-stack-specific knowledge (a framework, a database, a deployment platform) or project-specific runbooks, create a new skill directory:

```
.agents/skills/<skill-name>/
├── SKILL.md            # Required: instructions with YAML frontmatter
├── references/         # Optional: deep reference documentation
└── scripts/            # Optional: cross-platform helper scripts
```

Ensure `SKILL.md` starts with standard YAML frontmatter:
```yaml
---
name: <skill-name>
description: <What the skill does and when the agent should use it.>
---
```

You can also use `buddhi skills` to install pre-built skills (e.g. `buddhi skills --repo-to-skill`) or generate new skills from repositories.
