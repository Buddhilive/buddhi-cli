# Tasks: Token-Saving Command Output Filter (`buddhi scripts rtk`)

**Input**: Design documents from `/.buddhi/specs/010-rtk-style-token/` (`spec.md`, `plan.md`)

**Prerequisites**: `plan.md`, `spec.md`

**Organization**: Tasks are structured by phase and prioritized user stories (`P1` 🎯 MVP, `P2`, `P3`) for independent implementation and verifiable slices.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story identifier (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Concrete, unambiguous file paths in every task

---

## Phase 1: Setup & Foundational Infrastructure

**Purpose**: Directory scaffolding, filter data schemas, notice attribution, and foundational data structures.

- [x] T001 Create directory structure for RTK package at `src/buddhi/scripts/rtk/` and `src/buddhi/scripts/rtk/builtin_filters/`, plus test structure at `tests/rtk/` and `tests/rtk/fixtures/`.
- [x] T002 [P] Create `src/buddhi/scripts/rtk/NOTICE` with upstream Apache-2.0 attribution for `rtk-ai/rtk` and clear statement of changes and BUSL-1.1 exclusion.
- [x] T003 Define core JSON filter schema and validation models in `src/buddhi/scripts/rtk/filters.py` (supporting regex rules, replace, strip/keep, line dedup, head/tail limits, and inline test cases).
- [x] T004 Create generic fallback filter in `src/buddhi/scripts/rtk/generic.py` (ANSI strip, blank line collapse, duplicate line collapse, head/tail truncation with omitted line count).

---

## Phase 2: User Story 1 - Run a Command with Compressed Output (Priority: P1) 🎯 MVP

**Goal**: Deliver standalone CLI capability `buddhi scripts rtk run -- <cmd>` that executes commands, preserves exit codes, applies declarative JSON filters or generic fallback, protects error/failure lines, and writes raw failure output to a recovery tee log.

**Independent Test**: Run fixture tests for `git status`, `pytest`, `ruff`, and unknown commands. Verify output reduction ≥60%, zero dropped error lines, identical exit codes, and tee log creation on failure.

### Tests for User Story 1
- [x] T005 [P] [US1] Create unit tests for filter engine and error preservation in `tests/rtk/test_engine.py`.
- [x] T006 [P] [US1] Create unit tests for generic fallback filter in `tests/rtk/test_generic.py`.
- [x] T007 [P] [US1] Create unit tests for filter registry and matching in `tests/rtk/test_filters.py`.
- [x] T008 [P] [US1] Create integration tests for command runner, exit-code fidelity, and tee-on-failure in `tests/rtk/test_runner.py`.

### Implementation for User Story 1
- [x] T009 [US1] Implement filtering engine in `src/buddhi/scripts/rtk/engine.py` (strip, keep, replace, duplicate collapse, head/tail limit, empty fallback notice, and error-line guard).
- [x] T010 [US1] Implement subprocess command runner with streaming capture, exit-code preservation, and tee-on-failure raw log saving in `src/buddhi/scripts/rtk/runner.py`.
- [x] T011 [US1] Convert and port the initial set of 10 high-priority core filters into JSON under `src/buddhi/scripts/rtk/builtin_filters/` (`git-status.json`, `git-diff.json`, `git-log.json`, `pytest.json`, `ruff.json`, `mypy.json`, `uv.json`, `npm.json`, `cargo.json`, `docker.json`) with attribution metadata.
- [x] T012 [US1] Expose public API in `src/buddhi/scripts/rtk/__init__.py`.
- [x] T013 [US1] Wire `rtk` sub-app and implement `buddhi scripts rtk run` command in `src/buddhi/commands/scripts.py`.

**Checkpoint**: At this point, User Story 1 is fully functional and delivers an independently testable MVP.

---

## Phase 3: User Story 2 - Automatic Command Rewrite via Antigravity Hook (Priority: P2)

**Goal**: Automatically rewrite supported verbose shell commands issued by AI agents to route through `buddhi scripts rtk run`, while remaining strictly fail-open and respecting command boundaries and destructive guards.

**Independent Test**: Execute `tests/rtk/test_rewrite.py` and `tests/rtk/test_hook.py` covering allowed, skipped, compound, piped, already-wrapped, and malformed inputs.

### Tests for User Story 2
- [x] T014 [P] [US2] Create unit tests for rewrite decision logic (pipes, redirections, compounds, allowlists, quoting) in `tests/rtk/test_rewrite.py`.
- [x] T015 [P] [US2] Create unit tests for Antigravity hook stdin/stdout protocol and fail-open behavior in `tests/rtk/test_hook.py`.

### Implementation for User Story 2
- [x] T016 [US2] Implement rewrite decision module in `src/buddhi/scripts/rtk/rewrite.py` returning structured decisions (`allow`, `rewrite`, `skip` + reason).
- [x] T017 [US2] Add `rtk rewrite` subcommand to `src/buddhi/commands/scripts.py` for CLI inspections and script integration.
- [x] T018 [US2] Create fail-open Antigravity lifecycle hook in `.agents/hooks/rtk_hook.py` that exits 0 and rewrites tool commands via `overwrite.CommandLine` or payload replacement.
- [x] T019 [US2] Register `rtk_hook.py` under `PreToolUse` in `.agents/hooks.json` positioned safely after `guard_destructive.py`.

**Checkpoint**: User Stories 1 and 2 operate in tandem: commands run directly or get rewritten dynamically by the agent hook.

---

## Phase 4: User Story 3 - SDD Workflow Integration & Harness Conventions (Priority: P2)

**Goal**: Integrate the token-saving filter into SDD execution and verification workflows (`terminal-runner`, `/verify`, `/implement`), ensuring auditability with raw logs and providing permanent agent guidance.

**Independent Test**: Verify that `terminal-runner` agent instructions and `/verify` skill incorporate `buddhi scripts rtk run --` with raw log links on failures.

### Implementation for User Story 3
- [x] T020 [P] [US3] Create Antigravity rule `.agents/rules/rtk.md` defining token-saving conventions and raw output recovery instructions.
- [x] T021 [P] [US3] Create Antigravity skill `.agents/skills/rtk/SKILL.md` detailing how to use `buddhi scripts rtk`, interpret compressed output, and inspect raw logs.
- [x] T022 [P] [US3] Update `.agents/agents/terminal-runner.md` to run commands through `buddhi scripts rtk run --` and report compression stats / raw log paths.
- [x] T023 [P] [US3] Update `.agents/skills/verify/SKILL.md` and `.agents/skills/implement/SKILL.md` to document compressed evidence gathering and raw log auditing.
- [x] T024 [US3] Sync new rule, skill, and hook into `src/buddhi/templates/` so future harnesses generated by `buddhi` inherit the RTK integration.

**Checkpoint**: Agents actively utilize the RTK integration during SDD tasks without losing verification integrity.

---

## Phase 5: Broad Port of Upstream Filters (Priority: P2 Extension)

**Goal**: Broaden language and tool coverage by converting upstream Apache-2.0 TOML filters from `temp/rtk/src/filters/*.toml` into JSON format under `src/buddhi/scripts/rtk/builtin_filters/`.

**Independent Test**: Validate that all ported JSON filters pass structural validation and inline test definitions.

### Implementation for Broad Filter Port
- [x] T025 Create a conversion and validation utility script in `scripts/port_rtk_filters.py` to parse upstream TOML filters from `temp/rtk/src/filters/`, attach Apache-2.0 provenance metadata, and emit validated JSON files.
- [x] T026 Execute `scripts/port_rtk_filters.py` to port remaining ~50 filters across Python, Rust, Go, JS/TS, JVM, Cloud, and system tools into `src/buddhi/scripts/rtk/builtin_filters/`.
- [x] T027 [P] Add automated test in `tests/rtk/test_builtin_filters.py` validating that every builtin JSON filter has valid syntax, regex compilation, and runs embedded tests successfully.

**Checkpoint**: Complete language-agnostic filter library ported and tested under Apache-2.0 compliance.

---

## Phase 6: User Story 4 - Token Savings Analytics & Project Filter Trust (Priority: P3)

**Goal**: Track token savings locally in `.buddhi/rtk/runs.jsonl` with argument redaction, provide `buddhi scripts rtk gain` summary, and allow project-local custom filters in `.buddhi/rtk/filters/` with hash-pinned security trust.

**Independent Test**: Execute commands, verify `runs.jsonl` entries with redacted arguments, run `buddhi scripts rtk gain`, and verify project filter trust gating in `tests/rtk/test_trust.py`.

### Tests for User Story 4
- [x] T028 [P] [US4] Create unit tests for token estimation, redaction, and analytics in `tests/rtk/test_tracking.py`.
- [x] T029 [P] [US4] Create unit tests for project filter discovery, validation, and SHA-256 trust pinning in `tests/rtk/test_trust.py`.

### Implementation for User Story 4
- [x] T030 [US4] Implement token estimator, arg-redacting provenance recorder, and metrics aggregator in `src/buddhi/scripts/rtk/tracking.py`.
- [x] T031 [US4] Implement project filter hash verification and trust store in `src/buddhi/scripts/rtk/trust.py`.
- [x] T032 [US4] Add `buddhi scripts rtk gain`, `buddhi scripts rtk filters list|test|verify`, and `buddhi scripts rtk trust` commands to `src/buddhi/commands/scripts.py`.

**Checkpoint**: Observability, custom filters, and trust controls complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, upstream acknowledgments, changelog entries, and end-to-end quality gates.

- [x] T033 Update `ACKNOWLEDGMENTS.md` at project root with explicit attribution to `https://github.com/rtk-ai/rtk`, full Apache-2.0 upstream license text, description of ported components, and statement excluding BUSL-1.1 components.
- [x] T034 [P] Update `README.md` to document the new `buddhi scripts rtk` feature, Antigravity hook integration, token savings, and post-rewrite tool permission notice.
- [x] T035 [P] Update `CHANGELOG.md` under `[Unreleased]` with a comprehensive entry describing the RTK integration.
- [x] T036 Run full test and style verification: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src/ tests/`.
- [x] T037 Run `buddhi generate` to update the code graph and OKF documentation to include all new RTK symbols and modules.

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Can start immediately. Blocks Phase 2.
- **Phase 2 (US1 MVP)**: Depends on Phase 1. Delivers fully functional core CLI and filtering.
- **Phase 3 (US2 Hook)**: Depends on Phase 2. Delivers transparent hook rewrites.
- **Phase 4 (US3 SDD Integration)**: Can proceed after Phase 2 (runs in parallel with Phase 3).
- **Phase 5 (Broad Port)**: Depends on Phase 2 (filter engine must be ready).
- **Phase 6 (US4 Analytics & Trust)**: Depends on Phase 2 and Phase 5.
- **Phase 7 (Polish & Verification)**: Depends on completion of all implementation phases.
