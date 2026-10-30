# Tasks: Polished CLI Output, 1.0.0 Release

**Input**: Design documents from `.buddhi/specs/014-polished-cli-output/` (`spec.md`, `plan.md`)

**Organization**: Tasks are organized by user story into independently verifiable slices following the Spec-Driven Development (SDD) lifecycle.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Target user story (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task references concrete, exact file paths

---

## Phase 1: Setup & Presentation Infrastructure

**Purpose**: Establish the presentation package and UI structure.

- [x] T001 Initialize UI package module at `src/buddhi/ui/__init__.py`
- [x] T002 [P] Create unit test scaffold for UI formatting and banner rendering in `tests/test_ui_banner.py`
- [x] T003 [P] Create unit test scaffold for CLI versioning in `tests/test_cli_version.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core banner rendering, version resolution, and graceful degradation helpers that all user stories depend on.

**⚠️ CRITICAL**: Must be completed before user stories begin.

- [x] T004 Implement version resolver in `src/buddhi/__init__.py` (`importlib.metadata` with fallbacks for package name `buddhi-ai`, `buddhi`, and default `1.0.0`, exporting `__version__`)
- [x] T005 Implement ASCII art banner and terminal-width adaptive rendering in `src/buddhi/ui/banner.py` (66-column "BuddhiAI CLI" ASCII art, subtitle with version, and single-line fallback for `< 70` cols or non-TTY)
- [x] T006 Implement shared formatting primitives and layout components in `src/buddhi/ui/formatters.py` (status badges, metrics table, artifact lists, next-step callout panel)

**Checkpoint**: Foundation ready — UI components and version resolution are ready for story integration.

---

## Phase 3: User Story 1 - Branded `buddhi init` Output (Priority: P1) 🎯 MVP

**Goal**: Transform `buddhi init` command output from plain console lines into an attractive, structured developer-grade presentation with the ASCII banner, status summary, metrics, migration notices, and next steps.

**Independent Test**: Running `uv run buddhi init <temp_dir>` displays the ASCII banner, formatted summary panels, and exits with code 0 while creating all expected artifacts.

### Tests for User Story 1

- [x] T007 [P] [US1] Add unit tests in `tests/test_ui_banner.py` verifying full ASCII banner rendering on wide terminals (>= 70 cols) and single-line title fallback on narrow terminals (< 70 cols)
- [x] T008 [P] [US1] Add integration test in `tests/test_cli_init.py` asserting that `buddhi init` executes cleanly and includes "BuddhiAI CLI" in its output

### Implementation for User Story 1

- [x] T009 [US1] Integrate `render_banner` and structured formatting helpers into `src/buddhi/commands/init.py` (replace raw text prints with rich summary panel, metrics grid, migration notices, artifact bullet list, and next steps box)
- [x] T010 [US1] Verify non-TTY and error paths in `src/buddhi/commands/init.py` ensure clean stderr printing without styling anomalies on invalid paths

**Checkpoint**: User Story 1 is fully functional and can be demonstrated as a standalone MVP.

---

## Phase 4: User Story 2 - `--version` & Consistent Styling (Priority: P2)

**Goal**: Provide a `--version` / `-V` CLI flag showing the branded banner and version, and adopt shared status formatting in other commands like `generate` without showing the big banner.

**Independent Test**: Running `uv run buddhi --version` prints the banner and version string and exits 0. Running `uv run buddhi generate` uses consistent status icons without displaying the large ASCII banner.

### Tests for User Story 2

- [x] T011 [P] [US2] Add CLI tests in `tests/test_cli_version.py` verifying `buddhi --version` and `buddhi -V` print "BuddhiAI CLI" and the version, exiting with code 0
- [x] T012 [P] [US2] Add test in `tests/test_cli_version.py` asserting `--version` takes precedence over subcommands (eager execution)

### Implementation for User Story 2

- [x] T013 [US2] Add eager `version_callback` and `--version` / `-V` option to `@app.callback()` in `src/buddhi/cli.py`
- [x] T014 [US2] Update `src/buddhi/commands/generate.py` to use shared status formatting from `src/buddhi/ui/formatters.py` while keeping the big banner off

**Checkpoint**: User Stories 1 and 2 both work independently and harmoniously.

---

## Phase 5: User Story 3 - 1.0.0 Release Metadata & CHANGELOG (Priority: P2)

**Goal**: Prepare the package for 1.0.0 release by updating `pyproject.toml` and consolidating all unreleased features into a dedicated `[1.0.0]` section in `CHANGELOG.md`.

**Independent Test**: Package metadata version equals `1.0.0` and `CHANGELOG.md` contains `## [Unreleased]` followed by `## [1.0.0] - 2026-10-30`.

### Implementation for User Story 3

- [x] T015 [US3] Update version to `1.0.0` in `pyproject.toml`
- [x] T016 [US3] Reorganize `CHANGELOG.md` by moving current `[Unreleased]` contents under `## [1.0.0] - 2026-10-30`, adding the 1.0.0 release summary, and creating a new empty `## [Unreleased]` section
- [x] T017 [US3] Verify `__version__` in `src/buddhi/__init__.py` reports `1.0.0` when package is synced

**Checkpoint**: Release metadata is updated and synchronized.

---

## Phase 6: User Story 4 - Full-Tool Verification & Release Gate (Priority: P1)

**Goal**: Formally verify the entire codebase across all quality gates: test suite, linters, formatters, typecheckers, distribution build, and isolated smoke tests.

**Independent Test**: All verification commands exit with code 0 and release artifacts are generated.

### Verification Tasks

- [x] T018 [US4] Run code formatting checks: `uv run ruff format --check .`
- [x] T019 [US4] Run linting checks: `uv run ruff check .`
- [x] T020 [US4] Run static type checking: `uv run mypy src/ tests/`
- [x] T021 [US4] Run full automated test suite: `uv run pytest`
- [x] T022 [US4] Build distribution packages (`.whl` and `.tar.gz`) via `uv build`
- [x] T023 [US4] Perform end-to-end smoke verification of `buddhi --version`, `buddhi init`, and `buddhi generate` in a clean temporary directory

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Independent, starts immediately.
- **Foundational (Phase 2)**: Depends on Phase 1; blocks User Stories 1 & 2.
- **User Story 1 (Phase 3)**: Depends on Phase 2. MVP milestone.
- **User Story 2 (Phase 4)**: Depends on Phase 2 & 3.
- **User Story 3 (Phase 5)**: Depends on Phase 1 & 2 (can run alongside Phase 4).
- **User Story 4 (Phase 6)**: Runs after all implementation stories are complete as the final verification gate.

### Parallel Opportunities

- `T002` and `T003` can run in parallel during Setup.
- `T007` and `T008` can be written in parallel for US1.
- `T011` and `T012` can be written in parallel for US2.
- `T015` and `T016` can be executed in parallel during US3.
- `T018`, `T019`, and `T020` can run in parallel during US4 verification.

---

## Implementation Strategy

1. **Step 1**: Complete Setup + Foundational (`T001` - `T006`).
2. **Step 2**: Implement User Story 1 (`T007` - `T010`) → Validate `buddhi init` visual MVP.
3. **Step 3**: Implement User Story 2 (`T011` - `T014`) → Validate `buddhi --version` and command consistency.
4. **Step 4**: Implement User Story 3 (`T015` - `T017`) → Validate 1.0.0 release metadata and CHANGELOG.
5. **Step 5**: Execute User Story 4 (`T018` - `T023`) → Run the complete test suite, linter, typechecker, build, and smoke run.

