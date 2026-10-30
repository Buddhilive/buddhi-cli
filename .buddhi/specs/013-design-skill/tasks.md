# Tasks: DESIGN.md Skill & Design System Codification (`/design-md`)

**Branch**: `013-design-skill` | **Date**: 2026-10-30 | **Spec**: [.buddhi/specs/013-design-skill/spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/013-design-skill/spec.md) | **Plan**: [.buddhi/specs/013-design-skill/plan.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/013-design-skill/plan.md)

**Input**: Design documents from `/.buddhi/specs/013-design-skill/`

**Prerequisites**: `spec.md`, `plan.md`

**Organization**: Tasks are grouped by phase and user story to enable incremental, test-driven implementation and independent verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Mapped to user story (`US1`, `US2`, `US3`, `US4`)
- Exact file paths are specified for every task

---

## Phase 1: Setup & Foundational Infrastructure

**Purpose**: Create package structure, core data models, and test fixtures for the design-md engine.

- [x] T001 Create `src/buddhi/skills/design_md/__init__.py` exporting public API symbols.
- [x] T002 Implement core dataclasses in `src/buddhi/skills/design_md/models.py` (`DesignTokens`, `DesignFacts`, `DesignSection`, `ContrastFinding`, `DesignLintReport`, `MergeResult`).
- [x] T003 [P] Create initial test suite scaffolding and mock project fixtures (CSS variables, Tailwind config, tokens.json) in `tests/skills/test_design_md.py`.

**Checkpoint**: Foundation ready — core models and test fixtures in place.

---

## Phase 2: User Story 1 - Create and Update `DESIGN.md` via `/design-md` Engine & Script (Priority: P1) 🎯 MVP

**Goal**: Deliver the core two-layer `DESIGN.md` detection, generation, non-destructive merging, and WCAG 2.2 AA contrast linting engine, complete with CLI helper script `.agents/skills/design-md/scripts/detect_design_md.py`.

### Tests for User Story 1 ⚠️

- [x] T004 [P] [US1] Add unit tests for CSS variable, Tailwind config, and DTCG token detection in `tests/skills/test_design_md.py`.
- [x] T005 [P] [US1] Add unit tests for two-layer `DESIGN.md` generation (YAML frontmatter + 8 canonical Markdown sections) in `tests/skills/test_design_md.py`.
- [x] T006 [P] [US1] Add unit tests for non-destructive section and frontmatter merging (verifying custom `## Overview` prose and custom sections are preserved byte-for-byte) in `tests/skills/test_design_md.py`.
- [x] T007 [P] [US1] Add unit tests for WCAG 2.2 AA contrast evaluation and structural linting via `buddhi.scripts.contrast` in `tests/skills/test_design_md.py`.

### Implementation for User Story 1

- [x] T008 [US1] Implement repository facts and design token scanner in `src/buddhi/skills/design_md/detector.py` (parsing CSS variables, Tailwind configs, DTCG JSON, and providing clean neutral fallback tokens).
- [x] T009 [US1] Implement two-layer `DESIGN.md` builder in `src/buddhi/skills/design_md/generator.py` (generating YAML frontmatter + 8 canonical Markdown sections: `Overview`, `Colors`, `Typography`, `Layout`, `Elevation & Depth`, `Shapes`, `Components`, `Do's and Don'ts`).
- [x] T010 [US1] Implement section-aware parser and non-destructive merger in `src/buddhi/skills/design_md/merger.py` (preserving hand-written aesthetic prose, custom sections, and producing unified diffs).
- [x] T011 [US1] Implement structural validator and WCAG 2.2 AA contrast checker in `src/buddhi/skills/design_md/linter.py` (evaluating semantic color token pairs with `buddhi.scripts.contrast` and verifying canonical sections).
- [x] T012 [US1] Implement standalone cross-platform CLI helper script in `.agents/skills/design-md/scripts/detect_design_md.py` (`--diff`, `--apply`, `--lint`, `--json`, `--aesthetic`, `--root`).
- [x] T013 [US1] Create Antigravity skill definition in `.agents/skills/design-md/SKILL.md` (concise YAML frontmatter, progressive disclosure, and step-by-step runbook).
- [x] T014 [US1] Create detailed specification reference and aesthetic direction archetypes in `.agents/skills/design-md/references/design-md-spec.md`.

**Checkpoint**: User Story 1 (MVP) is fully functional — `detect_design_md.py` can detect tokens, generate `DESIGN.md`, non-destructively merge edits, and lint contrast.

---

## Phase 3: User Story 2 - Default Harness Scaffolding via `buddhi init` (Priority: P2)

**Goal**: Package `/design-md` into `buddhi-cli` templates so every new or existing project running `buddhi init` automatically scaffolds `.agents/skills/design-md/` idempotently.

### Tests for User Story 2 ⚠️

- [x] T015 [US2] Add automated integration tests in `tests/skills/test_design_md.py` verifying that `buddhi init` scaffolds `.agents/skills/design-md/` on a clean directory and leaves existing user edits untouched on repeat runs (`kept_existing`).

### Implementation for User Story 2

- [x] T016 [US2] Mirror packaged template files into `src/buddhi/templates/agents/skills/design-md/` (`SKILL.md`, `scripts/detect_design_md.py`, `references/design-md-spec.md`).
- [x] T017 [US2] Verify `src/buddhi/commands/init.py` and `sync_template_tree` sync report handles `design-md` cleanly without overwriting existing files.

**Checkpoint**: User Story 2 is complete — `buddhi init` scaffolds `.agents/skills/design-md/` reliably and idempotently.

---

## Phase 4: User Story 3 - SDD Workflow & Antigravity Specialist/Rule Integration (Priority: P3)

**Goal**: Integrate `DESIGN.md` awareness into the Spec-Driven Development (SDD) lifecycle (`/specify`, `/spec-plan`, `/implement`, `/verify`), `frontend-specialist`, and rules (`antislop.md`, `a11y.md`).

### Implementation for User Story 3

- [x] T018 [P] [US3] Update `frontend-specialist` agent in `.agents/agents/frontend-specialist.md` and `src/buddhi/templates/agents/agents/frontend-specialist.md` to consult `DESIGN.md` as primary design system contract.
- [x] T019 [P] [US3] Update SDD `/spec-plan` skill (`.agents/skills/spec-plan/SKILL.md` and `src/buddhi/templates/agents/skills/spec-plan/SKILL.md`) to include `DESIGN.md` Compliance Check in planning gate.
- [x] T020 [P] [US3] Update SDD `/specify` (`.agents/skills/specify/SKILL.md` and `src/buddhi/templates/agents/skills/specify/SKILL.md`), `/implement` (`.agents/skills/implement/SKILL.md`), and `/verify` (`.agents/skills/verify/SKILL.md`) to check `DESIGN.md` tokens and run `detect_design_md.py --lint`.
- [x] T021 [P] [US3] Update `.agents/rules/antislop.md` and `.agents/rules/a11y.md` (and their counterparts in `src/buddhi/templates/agents/rules/`) to reference `DESIGN.md` without exceeding the 24 KB per-file cap or 20,000-token rules budget.

**Checkpoint**: User Story 3 is complete — all SDD phases, specialist agents, and rules are aligned with `DESIGN.md`.

---

## Phase 5: User Story 4 - Documentation, Changelog & Attribution (Priority: P4)

**Goal**: Fulfill documentation and attribution requirements across `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, and `README.md`.

### Implementation for User Story 4

- [x] T022 [P] [US4] Update `CHANGELOG.md` under `## [Unreleased]` with a comprehensive entry for `/design-md`, token detection, non-destructive merging, WCAG contrast linting, and Antigravity/SDD integration.
- [x] T023 [P] [US4] Update `ACKNOWLEDGMENTS.md` with full attribution for the Google Labs / Google Stitch `DESIGN.md` specification (`https://stitch.withgoogle.com/docs/design-md/specification`, `https://github.com/google-labs-code/design.md`, Apache-2.0) and Google Antigravity Customization System documentation (`https://antigravity.google/docs/skills/` and `https://antigravity.google/docs/rules/`).
- [x] T024 [P] [US4] Update `README.md` to list and describe the `/design-md` skill and `DESIGN.md` design system codification in the agent harness overview.

---

## Phase 6: Polish & Quality Gates

**Purpose**: Final verification, code hygiene, and token ratchet validation.

- [x] T025 Run full test suite: `uv run pytest tests/skills/test_design_md.py`.
- [x] T026 [P] Run code formatting & linting: `uv run ruff check .` and `uv run ruff format --check .`.
- [x] T027 [P] Run typecheck: `uv run mypy src/ tests/`.
- [x] T028 Run token ratchet check: `uv run buddhi scripts check-file-size` (verifying all files remain strictly under 8,000 tokens).
- [x] T029 Template parity audit: verify all files in `.agents/` match their counterparts in `src/buddhi/templates/agents/`.
