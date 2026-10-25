# Tasks: `/agents-md` Skill (Create & Update AGENTS.md)

**Input**: Design documents from `.buddhi/specs/012-agents-skill/` (`spec.md`, `plan.md`)  
**Prerequisites**: `plan.md` (approved), `spec.md` (approved)  
**Organization**: Tasks are grouped by phase and user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- All task descriptions include exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency configuration and directory layout

- [x] T001 Add conditional dependency `tomli>=2.0.0; python_version < '3.11'` in `pyproject.toml` and sync environment via `uv sync`
- [x] T002 [P] Create package directory `src/buddhi/skills/agents_md/` and test fixtures directory `tests/fixtures/agents_md/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and multi-ecosystem fixtures that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Implement core models (`RepoFacts`, `CommandSet`, `AgentsSection`, `MergeResult`) in `src/buddhi/skills/agents_md/models.py`
- [x] T004 [P] Create mock repository fixture files for Python (uv/poetry/pip), Node (npm/pnpm), Rust (Cargo), Go (go.mod), and Makefile in `tests/fixtures/agents_md/`

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 - Generate AGENTS.md for a Repo Without One (Priority: P1) 🎯 MVP

**Goal**: Automatically inspect project manifests and synthesize a concise, evidence-grounded `AGENTS.md` (budgeted at ~12 lines) with zero guessing.

**Independent Test**: Run detection and generation against fixture projects and verify that generated `AGENTS.md` files have core block ≤ 12–15 lines with commands matching manifest evidence.

### Tests for User Story 1 ⚠️
> *Write these tests FIRST and ensure they fail before implementing the detector and generator.*

- [x] T005 [P] [US1] Unit and integration tests for detection and generation in `tests/test_agents_md.py` (covering Python uv/pytest/ruff/mypy, Node pnpm/vitest/eslint, Rust cargo, Go mod, Makefile, and line-budget assertions)

### Implementation for User Story 1

- [x] T006 [US1] Implement manifest and tool detector in `src/buddhi/skills/agents_md/detector.py` (detects project overview, install/build/test/lint/typecheck commands, and existing skills/rules)
- [x] T007 [US1] Implement concise core generator in `src/buddhi/skills/agents_md/generator.py` (~12-line core block with overview, commands, and pointers to `.agents/skills/`, `.agents/rules/`, and `.buddhi/docs/`)
- [x] T008 [US1] Export `detect_repo_facts` and `generate_agents_md` in `src/buddhi/skills/agents_md/__init__.py`

**Checkpoint**: Run `uv run pytest tests/test_agents_md.py -k "detect or generate"` to verify User Story 1 is fully functional in isolation.

---

## Phase 4: User Story 2 - Update an Existing AGENTS.md Safely (Priority: P2)

**Goal**: Safely update an existing `AGENTS.md` by parsing sections, refreshing detected commands, preserving hand-crafted custom sections byte-for-byte, and producing a unified diff for review before applying.

**Independent Test**: Update an `AGENTS.md` containing custom user sections (e.g. `## Engineering Principles & Non-Negotiables`) and verify custom sections remain character-identical while stale commands are updated in the unified diff.

### Tests for User Story 2 ⚠️

- [x] T009 [P] [US2] Unit tests for section parsing, custom section preservation, and unified diff output in `tests/test_agents_md.py`

### Implementation for User Story 2

- [x] T010 [US2] Implement section-aware parser and merger in `src/buddhi/skills/agents_md/merger.py` (parses `#`/`##` headings, updates managed sections, preserves unmanaged sections verbatim, and formats unified diff via `difflib`)
- [x] T011 [US2] Export `parse_agents_sections`, `merge_agents_md`, and `diff_agents_md` in `src/buddhi/skills/agents_md/__init__.py`

**Checkpoint**: Run `uv run pytest tests/test_agents_md.py -k "merge or diff"` to verify User Story 2 is fully functional and does not regress User Story 1.

---

## Phase 5: User Story 3 - Fit Antigravity, SDD & CLI Workflow (Priority: P3)

**Goal**: Deliver the `/agents-md` Antigravity skill, executable helper script, template bundling in `buddhi init`, CLI `--agents-md` flag in `buddhi skills`, and SDD `/spec-plan` integration.

**Independent Test**: Verify `buddhi skills --agents-md` installs the skill into a target directory, `src/buddhi/templates/agents/skills/agents-md/SKILL.md` contains valid frontmatter, and `buddhi skills` lists the skill in its inventory table.

### Tests for User Story 3 ⚠️

- [x] T012 [P] [US3] Unit tests for CLI `buddhi skills --agents-md` installation and registry listing in `tests/test_agents_md.py`

### Implementation for User Story 3

- [x] T013 [P] [US3] Create cross-platform executable helper script `scripts/detect_agents_md.py` (with `--diff`, `--apply`, `--json`, and `--root` CLI arguments) in `src/buddhi/templates/agents/skills/agents-md/scripts/detect_agents_md.py` and `.agents/skills/agents-md/scripts/detect_agents_md.py`
- [x] T014 [P] [US3] Create Antigravity skill instruction file in `.agents/skills/agents-md/SKILL.md` with YAML frontmatter (`name: agents-md`, description, progressive disclosure instructions)
- [x] T015 [US3] Bundle skill into template trees: `src/buddhi/templates/agents/skills/agents-md/` (for automated `buddhi init` sync) and `src/buddhi/templates/custom_skills/agents_md/` (for custom installer)
- [x] T016 [US3] Register `agents-md` in `src/buddhi/skills/registry.py` and add `--agents-md` option in `src/buddhi/commands/skills.py`
- [x] T017 [US3] Update SDD `/spec-plan` skill (`.agents/skills/spec-plan/SKILL.md` and `src/buddhi/templates/agents/skills/spec-plan/SKILL.md`) to reference `/agents-md` in the AGENTS.md Compliance Check gate

**Checkpoint**: Run `buddhi skills` to verify the table output and verify template synchronization.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Attribution, documentation, and codebase-wide verification

- [x] T018 [P] Update `CHANGELOG.md` under `[Unreleased]` documenting the `/agents-md` skill, generator, merge engine, and `buddhi skills --agents-md` CLI flag
- [x] T019 [P] Update `ACKNOWLEDGMENTS.md` with attribution for the AAIF benchmark study and Google Antigravity Skills & Rules documentation
- [x] T020 [P] Update `README.md` with `/agents-md` slash command and `buddhi skills --agents-md` documentation
- [x] T021 Run verification suite: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src/ tests/`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1); blocks all user stories.
- **User Story 1 (Phase 3 - P1 🎯 MVP)**: Depends on Phase 2; standalone slice.
- **User Story 2 (Phase 4 - P2)**: Depends on Phase 2 & Phase 3 (uses models and detection).
- **User Story 3 (Phase 5 - P3)**: Depends on Phase 3 & Phase 4 (packages detection & merge into skill and CLI).
- **Polish (Phase 6)**: Depends on all user stories being implemented.

### Parallel Opportunities
- `[P]` tasks across different files can execute simultaneously (e.g. T003 & T004 in Phase 2; T013, T014 in Phase 5; T018, T019, T020 in Phase 6).
- Test tasks are written first and proven to fail before the corresponding implementation tasks.
