# AGENTS.md

> Project instructions and conventions for AI coding agents.

## Overview
- **Project**: buddhi-cli
- **Type**: CLI / Agent Harness Generator
- **Primary Language/Runtime**: Python >= 3.10

## Commands
- **Install**: `uv sync`
- **Build**: `uv build`
- **Test**: `uv run pytest`
- **Lint & Format**: `uv run ruff check .` / `uv run ruff format --check .`
- **Typecheck**: `uv run mypy src/ tests/`

- **Knowledge Base & Code Graph**: Consult `.buddhi/docs/` (OKF concept documentation) and use Buddhi MCP tools (`buddhi_search`, `buddhi_read`) before grepping raw source files.
- **Spec-Driven Development (SDD)**: Features follow the SDD lifecycle:
  1. `/specify` — create feature branch and refine `spec.md` (use `/explore-unknowns` and `/auto-research` for pre-spec discovery)
  2. `/spec-plan` — synthesize technical architecture into `plan.md`
  3. `/tasks` — break down tasks by user story in `tasks.md`
  4. `/implement` — execute tasks story by story (run `/refactor-clean` checkpoints and log unprompted calls in `choices.md`)
  5. `/verify` — prove working behavior with real test evidence and visual verification gates (`/compare-screenshots`, `/screenshot-critique`)
  6. `/close-spec` — archive shipped spec to `.buddhi/specs/done/<branch>/` as a durable rationale record
- **Codebase Q&A**: Use `/ask <query>` to ask questions about architecture, components, and symbol relationships using the code graph.
- **Lightweight Planning**: Use `/quick-plan` for quick, non-SDD changes.

## Engineering Principles & Non-Negotiables
1. **Grounded Changes**: Ground all edits in real file paths and existing codebase conventions.
2. **Evidence-Based Verification**: Always run verification commands through `terminal-runner` and report actual exit codes and stdout/stderr output.
3. **Clean Code & Typings**: Preserve type annotations, docstrings, and existing comments.
