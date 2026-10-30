---
description: "Task list for adapting dzhng/skills and supportive scripts into buddhi-cli SDD workflow"
---

# Tasks: Adapt `dzhng/skills` & Supportive Scripts into `buddhi-cli` SDD Workflow

**Input**: Design documents from `.buddhi/specs/004-adapt-dzhng-skills/` (`spec.md`, `plan.md`, `research.md`)

**Prerequisites**: `spec.md`, `plan.md`, `research.md`

**Organization**: Phased breakdown grouped by user story (`US1` P1 MVP, `US2` P2, `US3` P3, `US4` P4) to enable independent implementation and testing of each slice.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Independent task across different files, safe for parallel execution.
- **[Story]**: User story identifier (`US1`, `US2`, `US3`, `US4`).

---

## Phase 1: Setup & Shared Infrastructure

**Purpose**: Directory scaffolding and prerequisite package declarations.

- [x] T001 [P] Ensure destination directory trees exist: `src/buddhi/scripts/`, `src/buddhi/templates/agents/skills/`, and `src/buddhi/templates/custom_skills/`
- [x] T002 [P] Verify pure-Python test harness dependencies and baseline command execution in `tests/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utilities, base helpers, and script registry infrastructure required before user stories can execute.

- [x] T003 Verify `src/buddhi/util/fsutil.py` template synchronization functions (`sync_template_tree`) handle nested `references/`, `assets/`, `kit/`, and `scripts/` directories without stripping non-markdown files
- [x] T004 [P] Update `src/buddhi/commands/scripts.py` to prepare subcommand registration slots for `check-file-size`, `visual-parity-diff`, and `receipts`
- [x] T005 [P] Update `src/buddhi/skills/registry.py` dataclasses and constants to support bundle-level installs (`GRAPHICS_SKILLS`)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — SDD-Complementary Skills & Enhanced SDD Lifecycle in `buddhi init` (Priority: P1) 🎯 MVP

**Goal**: Deliver 23 adapted SDD-complementary skills in `src/buddhi/templates/agents/skills/` (scaffolded by `buddhi init`) and enhance the 5 existing SDD skills (`specify`, `spec-plan`, `tasks`, `implement`, `verify`) with software-factory practices without changing the SDD workflow structure.

**Independent Test**: Run `uv run pytest tests/test_cli_init.py` and run `uv run buddhi init <tmp_dir>` to verify all 23 skills are copied with valid Antigravity frontmatter, `okf-context` code graph grounding, `terminal-runner` execution, and `.buddhi/specs/<branch>/` paths, while conflicting spec skills (`write-spec`, `implement-spec*`) and external CLI wrappers (`claude`, `codex`) are excluded.

### Tasks for User Story 1

- [x] T006 [P] [US1] Adapt pre-spec discovery skills into `src/buddhi/templates/agents/skills/`:
  - `src/buddhi/templates/agents/skills/explore-unknowns/SKILL.md` (+ 6 stage reference files in `references/`)
  - `src/buddhi/templates/agents/skills/auto-research/SKILL.md`
- [x] T007 [P] [US1] Adapt implementation, testing, and refactoring skills into `src/buddhi/templates/agents/skills/`:
  - `src/buddhi/templates/agents/skills/refactor-clean/SKILL.md`
  - `src/buddhi/templates/agents/skills/write-tests/SKILL.md`
  - `src/buddhi/templates/agents/skills/audit-tests/SKILL.md`
  - `src/buddhi/templates/agents/skills/audit-performance/SKILL.md`
  - `src/buddhi/templates/agents/skills/ratchet-files/SKILL.md` (pointing to `buddhi scripts check-file-size`)
  - `src/buddhi/templates/agents/skills/write-docs/SKILL.md`
  - `src/buddhi/templates/agents/skills/marketing-pages/SKILL.md`
- [x] T008 [P] [US1] Adapt review, decision audit, and spec lifecycle skills into `src/buddhi/templates/agents/skills/`:
  - `src/buddhi/templates/agents/skills/code-review/SKILL.md`
  - `src/buddhi/templates/agents/skills/review/SKILL.md`
  - `src/buddhi/templates/agents/skills/audit-choices/SKILL.md` (targeting `.buddhi/specs/<branch>/choices.md`)
  - `src/buddhi/templates/agents/skills/handoff-spec/SKILL.md` (targeting `.buddhi/specs/<branch>/`)
  - `src/buddhi/templates/agents/skills/close-spec/SKILL.md` (archiving to `.buddhi/specs/done/<branch>/`)
  - `src/buddhi/templates/agents/skills/eli5/SKILL.md`
  - `src/buddhi/templates/agents/skills/retro/SKILL.md`
- [x] T009 [P] [US1] Adapt visual review and design skills into `src/buddhi/templates/agents/skills/`:
  - `src/buddhi/templates/agents/skills/design-with-images/SKILL.md` (using Antigravity `image-generator` subagent)
  - `src/buddhi/templates/agents/skills/compare-screenshots/SKILL.md` (+ `references/reference-landmarks.md`, `references/subagent-visual-review.md`, using `buddhi scripts visual-parity-diff`)
  - `src/buddhi/templates/agents/skills/screenshot-critique/SKILL.md` (using `buddhi scripts receipts`)
  - `src/buddhi/templates/agents/skills/preview-shots/SKILL.md` (cross-platform commands: Windows, macOS, Linux, Antigravity artifacts)
- [x] T010 [P] [US1] Adapt authoring skills into `src/buddhi/templates/agents/skills/`:
  - `src/buddhi/templates/agents/skills/write-skills/SKILL.md`
  - `src/buddhi/templates/agents/skills/eval-skills/SKILL.md`
  - `src/buddhi/templates/agents/skills/audit-agents/SKILL.md` (+ `assets/example-agents.md`)
- [x] T011 [US1] Enhance the 5 existing SDD lifecycle skills in `src/buddhi/templates/agents/skills/`:
  - `specify/SKILL.md`: Link upstream `/explore-unknowns` and `/auto-research` for pre-spec discovery and seed experiments.
  - `spec-plan/SKILL.md`: Incorporate multi-perspective planning bias evaluations (fewest-slices vs risk-first vs seam-quality).
  - `tasks/SKILL.md`: Incorporate fog-of-war slice ordering and concrete verification boundaries.
  - `implement/SKILL.md`: Add periodic maintenance checkpoints (every 2-3 tasks), `/review` passes (`refactor-clean` -> `code-review` -> `write-docs`), and `/audit-choices` tracking.
  - `verify/SKILL.md`: Add visual verification gates (`/compare-screenshots`, `/screenshot-critique`) and prompt to archive completed specs with `/close-spec`.
- [x] T012 [US1] Update `src/buddhi/commands/init.py` summary output to reflect the expanded skill suite count and ensure idempotency.
- [x] T013 [US1] Add integration test `tests/test_cli_init_expanded_skills.py` validating that all 23 skills are scaffolded during `buddhi init`, user edits are preserved idempotently on re-runs, and all YAML frontmatter is well-formed.

**Checkpoint**: User Story 1 complete — all 23 SDD-complementary skills scaffolded and core SDD workflow enhanced.

---

## Phase 4: User Story 2 — Pure-Python Supportive Scripts under `buddhi scripts` (Priority: P2)

**Goal**: Implement `check-file-size`, `visual-parity-diff`, and `receipts` in pure Python stdlib (zero third-party binary/imaging dependencies) and integrate them into `buddhi scripts <subcommand>` with `--selftest` support.

**Independent Test**: Run `uv run pytest tests/test_scripts_check_file_size.py tests/test_scripts_visual_parity_diff.py tests/test_scripts_receipts.py` and run `--selftest` on each subcommand.

### Tasks for User Story 2

- [x] T014 [P] [US2] Implement `src/buddhi/scripts/check_file_size.py`:
  - Git subprocess runner (`rev-parse`, `ls-files -z`, `cat-file blob`, `cat-file -s`, `check-attr`, `diff --cached`)
  - Filter for programming languages and exclusions for `linguist-generated`/`linguist-vendored`
  - First-10-lines check for `@ratchet-files-ignore`
  - Audit mode (`--all`) listing violations sorted descending by size
  - Pre-commit ratchet mode (`<path>...`) allowing legacy oversized files in `HEAD` that shrank or stayed equal
  - Pure-Python `selftest()` and CLI runner returning exit codes `0`, `1`, `2`
- [x] T015 [P] [US2] Implement `src/buddhi/scripts/visual_parity_diff.py`:
  - Pure-Python stdlib PNG encoder/decoder (handling bit depth 8, color types 0, 2, 3 with PLTE, 4, 6, and filter types 0-4 using `zlib` and `struct`)
  - Alpha premultiplication and Rec.709 grayscale luminance calculation
  - Solo mode scene metrics: 4-bit color quantization, Shannon entropy, 3x3 neighbor gradient edge density, dominant color share, transparent share, luminance mean/p5/p95/contrast, writing `scene-metrics.json`
  - Pair diff mode: per-pixel MAE/RMSE, diff ratios (16, 32, 64), 3x3 Sobel edge convolution and edge energy ratio, YIQ anti-aliased `pixelmatch`, composite `parityDistance`, writing 8 diagnostic PNG artifacts and `visual-parity-diff.json`
  - Support for CLI flags (`--candidate-dir`, `--reference-dir`, `--out-dir`, `--crops-json`, `--report-order`, `--selftest`) and environment variables (`CANDIDATE_DIR`, etc.)
  - Built-in `selftest()` generating synthetic in-memory PNGs and verifying metrics
- [x] T016 [P] [US2] Implement `src/buddhi/scripts/receipts.py`:
  - Parser for fenced code blocks, indented blocks, and `$ <cmd>` shell transcripts
  - Execution receipt validator (requiring invocation line with allowed tool `TOOLS` including `buddhi` and non-empty output line)
  - Measurement claim extractor for numbers with attached units or nearby measurement verbs/units, and hex literals
  - Window proximity matching (default `--window 4`)
  - Artifact path and SHA-256 hash validator on disk (with ambiguous multi-pairing failure detection)
  - `--json`, `--label`, `--base`, and `--selftest` support, exiting `0` (pass), `1` (findings), `2` (error)
- [x] T017 [US2] Register subcommands in `src/buddhi/commands/scripts.py`:
  - Add `check-file-size` command
  - Add `visual-parity-diff` command
  - Add `receipts` command
- [x] T018 [P] [US2] Add unit and CLI integration tests in `tests/test_scripts_check_file_size.py`
- [x] T019 [P] [US2] Add unit and CLI integration tests in `tests/test_scripts_visual_parity_diff.py`
- [x] T020 [P] [US2] Add unit and CLI integration tests in `tests/test_scripts_receipts.py`

**Checkpoint**: User Story 2 complete — all 3 supportive CLI tools functioning with unit tests and passing `--selftest`.

---

## Phase 5: User Story 3 — Optional Graphics Skills via `buddhi skills` (Priority: P3)

**Goal**: Package the 5 specialized graphics skills (`renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, `xiaohei-illustrations`) in `src/buddhi/templates/custom_skills/` and register them in `buddhi skills` with individual flags and a `--graphics` bundle flag.

**Independent Test**: Run `uv run pytest tests/test_skills_graphics.py` and run `uv run buddhi skills --graphics -p <tmp_dir>` to verify complete template installation.

### Tasks for User Story 3

- [x] T021 [P] [US3] Create template packages under `src/buddhi/templates/custom_skills/`:
  - `renderer/` (`SKILL.md`, `__init__.py`)
  - `launch_video/` (`SKILL.md`, `__init__.py`)
  - `cinematic_shot/` (`SKILL.md`, `references/`, `__init__.py`)
  - `isometric_motion/` (`SKILL.md`, `references/`, `kit/`, `scripts/`, `examples/`, `__init__.py`)
  - `xiaohei_illustrations/` (`SKILL.md`, `references/`, `assets/`, `__init__.py`)
- [x] T022 [US3] Register the 5 graphics skills in `src/buddhi/skills/registry.py` with `SkillRegistryEntry` entries, flags (`--renderer`, `--launch-video`, `--cinematic-shot`, `--isometric-motion`, `--xiaohei-illustrations`), and a `GRAPHICS_SKILLS` bundle identifier list.
- [x] T023 [US3] Update `src/buddhi/commands/skills.py` to expose the 5 individual flags plus `--graphics` (installing all 5), and update the inventory table to highlight the graphics bundle.
- [x] T024 [US3] Add unit and CLI integration tests in `tests/test_skills_graphics.py` verifying individual installs, `--graphics` bundle install, idempotency, and directory structures.

**Checkpoint**: User Story 3 complete — graphics skills selectively installable on demand via `buddhi skills`.

---

## Phase 6: User Story 4 — Attribution, Licensing & Documentation Updates (Priority: P4)

**Goal**: Complete project attribution in `ACKNOWLEDGMENTS.md`, document new features in `README.md`, record changes in `CHANGELOG.md` under `[Unreleased]`, and update `AGENTS.md` / `agents-template.md`.

**Independent Test**: Verify file diffs and confirm all upstream licenses, contributors, and new CLI commands/skills are thoroughly documented.

### Tasks for User Story 4

- [x] T025 [US4] Update `ACKNOWLEDGMENTS.md` with a dedicated section for `dzhng/skills`:
  - Attribution to David Zhang (`https://github.com/dzhng/skills`, MIT License)
  - Sub-attributions: Matt Pocock, Thariq, wheresryan22, helloianneo
  - Full upstream MIT license text
- [x] T026 [US4] Update `README.md`:
  - Document the newly adapted skills in `.agents/skills/`
  - Document `buddhi scripts` subcommands (`check-file-size`, `visual-parity-diff`, `receipts`)
  - Document `buddhi skills` graphics flags and `--graphics` bundle
  - Link to `ACKNOWLEDGMENTS.md`
- [x] T027 [US4] Update `CHANGELOG.md` under `## [Unreleased]`:
  - Record the integration of 23 SDD-complementary skills and SDD lifecycle enhancements
  - Record `buddhi scripts` (`check-file-size`, `visual-parity-diff`, `receipts`)
  - Record `buddhi skills` graphics flags
  - Record `ACKNOWLEDGMENTS.md` updates
- [x] T028 [US4] Update root `AGENTS.md` and `src/buddhi/templates/agents/templates/agents-template.md` to reference the enhanced SDD lifecycle and new skills.

---

## Phase 7: Polish, Quality Gates & Regression Verification

**Purpose**: Validate code quality, formatting, static typing, and test passes across the entire project.

- [x] T029 Execute full self-tests via `terminal-runner`:
  - `uv run buddhi scripts check-file-size --selftest`
  - `uv run buddhi scripts visual-parity-diff --selftest`
  - `uv run buddhi scripts receipts --selftest`
- [x] T030 [P] Run code formatting and linting: `uv run ruff check src tests` and `uv run ruff format --check src tests` (verified zero errors in all new/modified files)
- [x] T031 [P] Run static type checking: `uv run mypy src tests` (verified zero errors in all new/modified files)
- [x] T032 Run full test suite: `uv run pytest` (163 passed in 15.14s)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1; blocks implementation of all user stories.
- **User Story 1 (Phase 3 - P1 MVP)**: Depends on Phase 2. Delivers the core 23 skills and SDD lifecycle enhancements.
- **User Story 2 (Phase 4 - P2)**: Depends on Phase 2. Can proceed in parallel with or right after US1.
- **User Story 3 (Phase 5 - P3)**: Depends on Phase 2. Can proceed in parallel with US1/US2.
- **User Story 4 (Phase 6 - P4)**: Depends on US1, US2, US3 to capture all documentation and licensing accurately.
- **Polish (Phase 7)**: Final verification gate across the entire codebase.

### Parallel Opportunities
- Within Phase 3: T006, T007, T008, T009, T010 can be authored in parallel across distinct skill directories.
- Within Phase 4: T014, T015, T016 are independent script files and can be authored in parallel.
- Within Phase 5: T021 template packages can be created in parallel.
- In Phase 7: Ruff and Mypy checks can run in parallel.

