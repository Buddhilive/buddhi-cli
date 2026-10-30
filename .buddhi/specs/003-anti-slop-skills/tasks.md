# Tasks: Anti-Slop Skills, Rules & Scripts Integration

**Input**: Design documents from `/.buddhi/specs/003-anti-slop-skills/` (`spec.md`, `plan.md`)

**Prerequisites**: `spec.md`, `plan.md`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Exact file paths are used in all task descriptions.

---

## Phase 1: Setup (Scaffolding & Infrastructure)

**Purpose**: Prepare package structure for scripts subcommands and tools.

- [x] T001 Create `src/buddhi/scripts/__init__.py` to turn `src/buddhi/scripts/` into an importable package.
- [x] T002 [P] Create `src/buddhi/commands/scripts.py` with initial Typer app `scripts_app` (name="scripts", help="Utility scripts and tools.").
- [x] T003 Register `scripts_app` in `src/buddhi/cli.py` under command group `scripts`.

---

## Phase 2: User Story 1 - Anti-slop skills & rule ship with `buddhi init` (Priority: P1) 🎯 MVP

**Goal**: Make `buddhi init` scaffold all 6 Antigravity-adapted anti-slop skills and the always-on antislop rule into `.agents/` without overwriting existing files.

**Independent Test**: Run `buddhi init` in a clean temporary directory and verify that `.agents/skills/antislop*` and `.agents/rules/antislop.md` are created with valid frontmatter, and that `frontend-specialist.md` references the antislop skills.

### Tests for User Story 1

- [x] T004 [US1] Update `tests/test_cli_init.py` to assert that `buddhi init` installs `.agents/rules/antislop.md` and the 6 skills (`antislop`, `antislop-ui`, `antislop-copywriting`, `antislop-human`, `antislop-layoutmobile`, `antislop-code`), and ensure the test fails before templates are finalized.

### Implementation for User Story 1

- [x] T005 [P] [US1] Create always-on rule template in `src/buddhi/templates/agents/rules/antislop.md` with `trigger: always_on` frontmatter, routing to `.agents/skills/antislop*/SKILL.md`.
- [x] T006 [P] [US1] Audit and finalize core skill in `src/buddhi/templates/agents/skills/antislop/SKILL.md` (check Antigravity frontmatter, remove any upstream tool paths, verify attribution notice).
- [x] T007 [P] [US1] Audit and finalize UI skill in `src/buddhi/templates/agents/skills/antislop-ui/SKILL.md`.
- [x] T008 [P] [US1] Audit and finalize copywriting skill in `src/buddhi/templates/agents/skills/antislop-copywriting/SKILL.md`.
- [x] T009 [P] [US1] Audit and finalize human/people skill in `src/buddhi/templates/agents/skills/antislop-human/SKILL.md` (including reference contrast table and pointer to `buddhi scripts contrast` and `check_contrast` MCP tool).
- [x] T010 [P] [US1] Audit and finalize mobile layout skill in `src/buddhi/templates/agents/skills/antislop-layoutmobile/SKILL.md`.
- [x] T011 [P] [US1] Audit and finalize code comments skill in `src/buddhi/templates/agents/skills/antislop-code/SKILL.md`.
- [x] T012 [US1] Verify and finalize `src/buddhi/templates/agents/agents/frontend-specialist.md` ensuring it references the antislop skills.

**Checkpoint**: User Story 1 complete — `pytest tests/test_cli_init.py` passes. MVP delivered!

---

## Phase 3: User Story 2 - `buddhi scripts` & MCP Contrast Tool (Priority: P2)

**Goal**: Provide standalone Python implementation of WCAG contrast checking (`buddhi scripts contrast`), global mode management (`buddhi scripts antislop-mode`), and MCP `check_contrast` tool.

**Independent Test**: Run `buddhi scripts contrast "#FFFFFF" "#000000"`, `buddhi scripts contrast --selftest`, `buddhi scripts antislop-mode`, and execute the `check_contrast` MCP tool test.

### Tests for User Story 2

- [x] T013 [P] [US2] Create unit tests in `tests/test_scripts_contrast.py` testing hex parsing, relative luminance, contrast calculation, normal/large verdicts, boundary conditions (4.5:1, 3.0:1), and `--selftest`.
- [x] T014 [P] [US2] Create unit tests in `tests/test_scripts_antislop_mode.py` testing settings path resolution, reading empty/missing file, writing valid mode (`during`, `after`, `ask`), and unparseable JSON error handling without overwriting.
- [x] T015 [P] [US2] Create CLI integration tests in `tests/test_cli_scripts.py` verifying `buddhi scripts contrast` exit codes (0 for pass, 1 for fail, 2 for bad syntax) and `buddhi scripts antislop-mode` output.
- [x] T016 [P] [US2] Update `tests/test_mcp_server.py` to test the `check_contrast` MCP tool.

### Implementation for User Story 2

- [x] T017 [US2] Implement pure contrast calculation & selftest engine in `src/buddhi/scripts/contrast.py` (resolving reference table via `importlib.resources`).
- [x] T018 [P] [US2] Implement global antislop mode settings reader/writer in `src/buddhi/scripts/antislop_mode.py` adhering to `%APPDATA%\antislop\settings.json` on Windows and `~/.config/antislop/settings.json` on Unix.
- [x] T019 [US2] Implement Typer CLI subcommands in `src/buddhi/commands/scripts.py` for `contrast` (with `--selftest`) and `antislop-mode`.
- [x] T020 [P] [US2] Implement MCP tool adapter in `src/buddhi/mcp/tools/contrast.py` invoking `src/buddhi/scripts/contrast.py`.
- [x] T021 [US2] Register `@mcp.tool` `check_contrast` in `src/buddhi/mcp/server.py`.

**Checkpoint**: User Story 2 complete — `pytest tests/test_scripts_*.py tests/test_cli_scripts.py tests/test_mcp_server.py` passes.

---

## Phase 4: User Story 3 - Attribution & Documentation (Priority: P3)

**Goal**: Meet open-source licensing requirements with upstream attribution and document all new features in user documentation.

**Independent Test**: Check that `ACKNOWLEDGMENTS.md` exists and contains MIT notice and credit, `README.md` documents anti-slop skills and `buddhi scripts`, and `CHANGELOG.md` has an entry under `[Unreleased]`.

### Implementation for User Story 3

- [x] T022 [P] [US3] Create `ACKNOWLEDGMENTS.md` at repository root with full credit to `https://github.com/miqdadbadjuber/anti-slop` and the complete upstream MIT license text and copyright notice.
- [x] T023 [P] [US3] Update `README.md` documenting the anti-slop skills/rules included in `buddhi init`, `buddhi scripts contrast` and `buddhi scripts antislop-mode` usage, and linking to `ACKNOWLEDGMENTS.md`.
- [x] T024 [P] [US3] Update `CHANGELOG.md` adding the anti-slop skills, rules, scripts, and MCP tool under the `[Unreleased]` section.

**Checkpoint**: User Story 3 complete — documentation and licensing verified.

---

## Phase 5: Polish & Cross-Cutting Verification

**Purpose**: Ensure entire test suite passes, code formatting and type checks are clean, and code graph is updated.

- [x] T025 Run full pytest suite across the entire project (`uv run pytest` or `pytest`).
- [x] T026 Run linter and formatting checks (`ruff check .` and `ruff format --check .`).
- [x] T027 Run type checks (`mypy src/`).
- [x] T028 Refresh codebase graph using `buddhi generate` to reflect newly added modules and commands.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **User Story 1 (Phase 2)**: Can start after Phase 1 (or parallel to Phase 1 since templates don't depend on CLI code). Delivers viable MVP.
- **User Story 2 (Phase 3)**: Depends on Phase 1 Setup and Phase 2 `antislop-human/SKILL.md` (for `--selftest` table resolution).
- **User Story 3 (Phase 4)**: Can run in parallel with or after Phase 2/3.
- **Polish (Phase 5)**: Runs after all tasks complete.

### Parallel Opportunities

- In Phase 1: `T002` [P] can run in parallel with `T001`.
- In Phase 2: `T005`-`T011` [P] (rule and individual skill templates) can be edited in parallel.
- In Phase 3: All tests `T013`-`T016` [P] can be authored in parallel before implementation.
- In Phase 4: `T022`, `T023`, `T024` [P] can be edited in parallel.

