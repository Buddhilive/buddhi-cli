# Implementation Plan: `/agents-md` Skill (Create & Update AGENTS.md)

**Branch**: `012-agents-skill` | **Date**: 2026-10-29 | **Spec**: [spec.md](file:///C:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/012-agents-skill/spec.md)

**Input**: Feature specification from `.buddhi/specs/012-agents-skill/spec.md`

## Summary

The `AGENTS.md` file provides agents with essential operational context (environment setup, build/test/lint commands, key components, and pointers to granular skills and docs). In July 2026, the Agentic AI Foundation (AAIF) benchmark study showed that including `AGENTS.md` reduces diff sizes by 26%, wall clock time by 27%, and tokens by 25% by preventing agents from getting lost in command trial-and-error loops. Crucially, the benchmark emphasizes **brevity**: keeping top-line `AGENTS.md` files concise (~12 lines) rather than bloated manuals.

This feature implements an Antigravity-optimized `/agents-md` skill and Python engine for `buddhi-cli` that:
1. **Detects** repository setup, tooling, and commands from manifests (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `Makefile`, GitHub Actions, etc.), the code graph, and `.buddhi/docs/`.
2. **Generates** a concise, structured `AGENTS.md` core block (budgeted at ~12 lines: overview, verified build/test/lint commands, key components, and pointers to `.agents/skills/`, `.agents/rules/`, and `.buddhi/docs/`).
3. **Updates** existing `AGENTS.md` files safely through a section-aware merge engine that preserves user-authored sections byte-for-byte, generates a unified diff, and halts for user confirmation before writing to disk.
4. **Integrates** with Google Antigravity discovery and SDD workflows:
   - Placed in `.agents/skills/agents-md/SKILL.md` (invocable via `/agents-md`).
   - Bundled in `src/buddhi/templates/agents/skills/agents-md/` (automatically scaffolded on `buddhi init`).
   - Registered in `buddhi skills` with `--agents-md` CLI flag for targeted installation into existing repositories.
   - Connected with the SDD `AGENTS.md Compliance Check` in `/spec-plan` and harness conventions.
5. Documents references in `ACKNOWLEDGMENTS.md`, `CHANGELOG.md` under `[Unreleased]`, and `README.md`.

---

## Technical Context

**Language/Version**: Python >= 3.10
- Uses `tomllib` (Python 3.11+) with fallback to `tomli` on Python 3.10.
- Standard library modules: `pathlib`, `json`, `difflib`, `re`, `shutil`, `subprocess`.

**Primary Dependencies**:
- Existing workspace dependencies: `typer`, `rich`, `pathspec`.
- Added dependency: `tomli>=2.0.0; python_version < '3.11'` in `pyproject.toml` (already satisfied in existing virtualenv).

**Storage**:
- File system: repo-root `AGENTS.md`. No database changes.

**Testing**:
- `pytest`: unit and integration tests under `tests/test_agents_md.py` covering multi-language manifests (Python uv/pip/poetry, Node npm/pnpm/yarn, Rust Cargo, Go mod, Make), line count limits, section merge byte-preservation, diff generation, and CLI flag handling.

**Target Platform**:
- Cross-platform: Windows, macOS, Linux (pathlib-based, newline-preserving).

**Project Type**:
- CLI and Antigravity Agent Skill.

**Performance Goals**:
- Detection and generation run under 100ms on typical repositories.

**Constraints**:
- Strict Brevity Constraint: core block of generated `AGENTS.md` must stay ~12-15 lines.
- Non-destructive Update: hand-crafted sections in existing `AGENTS.md` must be preserved byte-for-byte.
- No Guessing: every detected command must trace to real repo manifest/config evidence.

---

## Constitution & Platform Grounding

### 1. Google Antigravity Rules Specification (`https://antigravity.google/docs/rules/`)
- **Discovery**: Standalone `AGENTS.md` (or `GEMINI.md`) is discovered by walking up from the current directory to the repository root and is always active for its directory scope.
- **Budget Limits**: Antigravity imposes a **24 KB** per-file limit and a shared **20,000-token rules budget** (`defaultRulesBudget`). Over-budget rules are demoted to file path pointers. Keeping `AGENTS.md` tightly bounded (~12 lines) ensures it never overwhelms this budget.
- **Format**: Plain Markdown with no frontmatter.

### 2. Google Antigravity Skills Specification (`https://antigravity.google/docs/skills/`)
- **Location**: `.agents/skills/<skill_name>/SKILL.md`.
- **Frontmatter**: Required YAML frontmatter with `name` (lowercase, hyphenated) and `description` (third-person trigger description explaining *what* and *when* to invoke).
- **Progressive Disclosure**: Detailed operational guidelines and reference templates live under `references/`, keeping the root `SKILL.md` token-efficient.
- **Executable Helpers**: Command sequences are encapsulated in `scripts/detect_agents_md.py` so the agent can invoke them cross-platform.

### 3. Agentic AI Foundation (AAIF) Benchmark (`https://aaif.io/blog/measuring-agents-md-what-five-runs-show-that-one-doesn-t`)
- 26% reduction in diff size, 27% reduction in wall clock time, 25% reduction in token consumption.
- Top takeaway: Eliminate worst-case loops where agents run incorrect build or test commands.

---

## AGENTS.md Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify that the planned architecture and changes comply with project rules, commands, and boundaries defined in `AGENTS.md` (or `.agents/rules/`).

- [x] **Project build & test commands adhered to**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/ tests/`.
- [x] **Architectural constraints respected**: Pure Python 3.10+ implementation, standard library + `tomli` fallback, template sync via `buddhi.templates.agents`, idempotent CLI installer.
- [x] **No unapproved external dependencies introduced**: Only standard conditional `tomli` for Python 3.10 compatibility.

---

## Architectural Evaluation & Trade-off Lenses

### Lens 1: Fewest-Slices
- Build a single, cohesive engine package `src/buddhi/skills/agents_md/` with three focused modules:
  1. `detector.py`: Scans project root for manifests, tool configurations, existing rules, and skills. Emits a typed `RepoFacts` dataclass.
  2. `generator.py`: Renders `RepoFacts` into a clean, concise ~12-line `AGENTS.md`.
  3. `merger.py`: Parses an existing `AGENTS.md` into recognized headers (`# AGENTS.md`, `## Overview`, `## Commands`, `## Skills & Architecture`) and unmanaged custom sections. Updates recognized sections while leaving custom sections unchanged. Produces a unified diff.
- Expose via CLI:
  - Add `--agents-md` to `src/buddhi/commands/skills.py` and `src/buddhi/skills/registry.py`.
  - Bundle template in `src/buddhi/templates/agents/skills/agents-md/` for automatic `buddhi init` sync.
  - Provide `.agents/skills/agents-md/SKILL.md` and helper script for slash command `/agents-md`.

### Lens 2: Risk-First
- **Risk: Accidental overwriting of user customizations.**
  - *Mitigation*: Section-level parser identifies unknown headings (e.g., `## Engineering Principles & Non-Negotiables`, `## Domain Rules`) and retains their verbatim content and ordering. The update workflow always prints a diff and requires user confirmation before modifying the file.
- **Risk: Command guessing / hallucination.**
  - *Mitigation*: Strict evidence-based detection. If a project has `pyproject.toml` with `[tool.pytest]`, it emits `pytest`. If `uv.lock` is present, it uses `uv run pytest`. If no linter is detected, it does not invent one.
- **Risk: Bloat / exceeding the 12-line budget.**
  - *Mitigation*: Strictly constrained generator template:
    1. `# AGENTS.md`
    2. Empty line
    3. `> [One-line overview]`
    4. Empty line
    5. `## Commands`
    6-10. Five core commands (`Install`, `Build`, `Test`, `Lint`, `Typecheck`)
    11. Empty line
    12. `## Skills & Architecture` (pointers to `.agents/skills/`, `.agents/rules/`, `.buddhi/docs/`)

### Lens 3: Seam-Quality
- CLI commands (`buddhi skills --agents-md`), harness generation (`buddhi init`), and the interactive agent skill (`/agents-md`) all consume the exact same underlying `buddhi.skills.agents_md` library and helper script, eliminating code duplication or drift.

---

## Project Structure

### Documentation & Specifications
```text
.buddhi/specs/012-agents-skill/
├── spec.md              # Feature specification
└── plan.md              # This architecture plan
```

### Source Code
```text
src/buddhi/skills/
├── agents_md/
│   ├── __init__.py      # Package export: detect, generate, merge, diff
│   ├── detector.py      # Manifest and tool detection engine
│   ├── generator.py     # Concise AGENTS.md formatter (~12 lines)
│   ├── merger.py        # Section-aware parser and unified diff generator
│   └── models.py        # Typed dataclasses: RepoFacts, AgentsSection, MergeResult
├── registry.py          # Register 'agents-md' entry in _SKILL_REGISTRY
└── installer.py         # Support skill installation into .agents/skills/

src/buddhi/commands/
└── skills.py            # Add --agents-md CLI option to 'buddhi skills'

src/buddhi/templates/
├── agents/skills/agents-md/
│   ├── SKILL.md         # Antigravity skill instruction file
│   └── scripts/
│       └── detect_agents_md.py  # Standalone CLI/runner helper script
└── custom_skills/agents_md/     # Optional standalone template for installer
    └── SKILL.md

.agents/skills/agents-md/
├── SKILL.md             # Active repo skill
└── scripts/
    └── detect_agents_md.py

tests/
├── fixtures/agents_md/  # Sample repo manifests (Python, Node, Rust, Go, Make)
└── test_agents_md.py    # Unit & integration test suite
```

### Documentation & Attribution Updates
- `CHANGELOG.md`: Entry under `[Unreleased]` detailing the `/agents-md` skill, generator, merge engine, and CLI flag.
- `ACKNOWLEDGMENTS.md`: Attribution for Agentic AI Foundation (AAIF) benchmark study and Google Antigravity Skills & Rules documentation.
- `README.md`: Document `/agents-md` in skills table and `buddhi skills --agents-md` CLI command.

---

## Detailed Component Design

### 1. `RepoFacts` Detection (`src/buddhi/skills/agents_md/detector.py`)
Scans repository root for:
- **Project Name & Overview**:
  - `pyproject.toml` (`project.name`, `project.description`)
  - `package.json` (`name`, `description`)
  - `Cargo.toml` (`package.name`, `package.description`)
  - `README.md` first headline and paragraph.
- **Package Manager & Environment Setup**:
  - Python: `uv.lock` -> `uv sync`, `poetry.lock` -> `poetry install`, `Pipfile.lock` -> `pipenv install`, `requirements.txt` -> `pip install -r requirements.txt`.
  - Node: `pnpm-lock.yaml` -> `pnpm install`, `yarn.lock` -> `yarn install`, `bun.lockb` -> `bun install`, `package-lock.json` -> `npm install`.
  - Rust: `Cargo.lock` -> `cargo build`.
  - Go: `go.mod` -> `go mod download`.
- **Test Command**:
  - Python: `pytest`, `unittest`.
  - Node: `npm test`, `pnpm test`, `vitest`, `jest`.
  - Rust: `cargo test`.
  - Go: `go test ./...`.
- **Lint & Format**:
  - Python: `ruff check .` / `ruff format --check .`, `flake8`, `black`.
  - Node: `eslint`, `biome`, `prettier`.
  - Rust: `cargo clippy`, `cargo fmt --check`.
  - Go: `golangci-lint run`.
- **Typecheck**:
  - Python: `mypy`, `pyright`, `basedpyright`.
  - Node: `tsc --noEmit`.
- **Skills & Rules**:
  - Discovers existing skills in `.agents/skills/` and rules in `.agents/rules/`.
  - References `.buddhi/docs/` (OKF concept documentation) if initialized.

### 2. Concise Core Generator (`src/buddhi/skills/agents_md/generator.py`)
Generates the core markdown:
```markdown
# AGENTS.md

> <Project Name> - <Brief 1-sentence description>.

## Commands
- **Install**: `<install_cmd>`
- **Build**: `<build_cmd>`
- **Test**: `<test_cmd>`
- **Lint & Format**: `<lint_cmd>`
- **Typecheck**: `<typecheck_cmd>`

## Agent Conventions & Skills
- Consult `.agents/skills/` for granular workflows and `.agents/rules/` for codebase constraints.
- Consult `.buddhi/docs/` for code graph and symbol documentation.
```
*Exact line count*: 12 lines. Meets the AAIF benchmark brevity guideline.

### 3. Section-Aware Merge Engine (`src/buddhi/skills/agents_md/merger.py`)
- Splits existing file into `Section(heading, level, content)`.
- Updates known sections:
  - `# AGENTS.md` and blockquote overview.
  - `## Commands`: updates detected command lines; if a user had custom command comments, merges or updates values without dropping user flags.
  - `## Agent Conventions & Skills`: ensures pointers exist.
- **Preserves all user sections verbatim**:
  - Sections such as `## Engineering Principles & Non-Negotiables`, `## Architecture Notes`, `## Security Guidelines` are retained in their exact original order and text.
- Generates a standard unified diff string (`difflib.unified_diff`).

### 4. Skill Workflow (`SKILL.md`)
1. **Analyze**: Run `python scripts/detect_agents_md.py --diff` via `terminal-runner`.
2. **Review**: Present detected commands and generated diff to the user.
3. **Confirm & Apply**: If user confirms (or if no file exists), write the file.
4. **Handoff**: If user wants to audit principles of an existing file, recommend `/audit-agents`.

---

## Accessibility (A11Y) Evaluation

This feature is entirely CLI- and markdown-based; there are no frontend, UI, web, or mobile surfaces.
- A11Y requirement: **N/A**.
- Formatted markdown output in `AGENTS.md` complies with standard Markdown heading hierarchy (`#`, `##`) for accessible screen reader navigation.

---

## Verification & Testing Plan

1. **Unit Tests (`tests/test_agents_md.py`)**:
   - `test_detect_python_uv_project`: Fixture with `pyproject.toml`, `uv.lock`, pytest, ruff, mypy.
   - `test_detect_node_project`: Fixture with `package.json`, pnpm lock, vitest, eslint, tsc.
   - `test_detect_rust_project`: Fixture with `Cargo.toml`.
   - `test_generate_concise_budget`: Assert generated file has 12–15 lines.
   - `test_merge_preserves_custom_sections`: Existing file with custom `## Architecture Notes` and `## Security` must keep them byte-identical.
   - `test_merge_updates_stale_command`: Updating `pytest` to `uv run pytest` reflects properly in diff and merged output.
   - `test_diff_output`: Verifies valid unified diff output format.
   - `test_cli_flag`: Verify `buddhi skills --agents-md` installs into target path.
2. **Harness Integration Verification**:
   - Verify `src/buddhi/templates/agents/skills/agents-md/SKILL.md` exists and contains valid frontmatter.
   - Run `uv run pytest` to ensure all tests pass.
   - Run `uv run ruff check .` and `uv run ruff format --check .`.
   - Run `uv run mypy src/ tests/`.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None      | N/A        | N/A                                 |
