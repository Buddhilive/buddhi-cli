# Tasks: Codebase Q&A Workflow (/ask), Graph Refresh Integration, and MCP Root Configuration

**Feature Branch**: `002-ask-workflow-and`
**Spec**: [.buddhi/specs/002-ask-workflow-and/spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/002-ask-workflow-and/spec.md)
**Plan**: [.buddhi/specs/002-ask-workflow-and/plan.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/002-ask-workflow-and/plan.md)

---

## Phase 1: Setup

**Purpose**: Verify baseline repository state and initialize task tracking.

- [x] T001 Inspect workspace state, verify active branch and test suite baseline in `c:/DevDojo/Buddhi/buddhi-cli`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix test harness isolation and stdout encoding so subsequent stories can be tested reliably.

- [x] T002 Isolate `test_sdd_dry_run_create` working directory in `tests/test_sdd.py` using `tmp_path` and `monkeypatch.chdir(tmp_path)` to prevent collisions with real `.buddhi/specs` folders.
- [x] T003 [P] Ensure UTF-8 stdout encoding compatibility in `src/buddhi/sdd/setup_tasks.py` on Windows systems.

**Checkpoint**: Baseline test suite passes completely.

---

## Phase 3: User Story 1 - Configure Workspace Root in MCP Config & Support `--root` in MCP Server (Priority: P1) 🎯 MVP

**Goal**: Enable `buddhi-mcp` (and `buddhi mcp`) to accept `--root`, anchor database resolution and workspace file searches to that root, and have `buddhi init` automatically configure `args: ["--root", "<resolved_root>"]` in `.agents/mcp_config.json`.

**Independent Test**:
Run `buddhi init <tmp_path>`, verify `.agents/mcp_config.json` has `args: ["--root", ...]`, start `buddhi-mcp --root <tmp_path>` from outside the directory, and call `buddhi_search(query=...)` without `cwd`. Verify it locates the database and returns correct results.

### Tests for User Story 1

- [x] T004 [P] [US1] Add unit tests in `tests/test_mcp_server.py` verifying `--root` argument parsing, `OVERRIDE_ROOT` setting, and `_get_db_path()` resolution.
- [x] T005 [P] [US1] Add integration assertions in `tests/test_cli_init.py` verifying `mcp_config.json` contains `args: ["--root", str(tmp_path.resolve())]`.

### Implementation for User Story 1

- [x] T006 [US1] Implement `OVERRIDE_ROOT` global variable and `--root` (and positional) argument parsing in `src/buddhi/mcp/server.py`.
- [x] T007 [US1] Update `_get_db_path(cwd=None)` in `src/buddhi/mcp/server.py` to prioritize `OVERRIDE_ROOT` when `cwd` is omitted.
- [x] T008 [US1] Update `_native_grep_search` and `execute_buddhi_search` in `src/buddhi/mcp/tools/search.py` to search against `OVERRIDE_ROOT`.
- [x] T009 [US1] Update `execute_buddhi_read` in `src/buddhi/mcp/tools/read.py` to resolve relative filepaths and native fallbacks using `OVERRIDE_ROOT`.
- [x] T010 [US1] Add `--root` option to `buddhi mcp` CLI command in `src/buddhi/commands/mcp.py` to forward root path to `OVERRIDE_ROOT`.
- [x] T011 [US1] Update `buddhi init` in `src/buddhi/commands/init.py` to configure `.agents/mcp_config.json` with `args: ["--root", str(root.resolve())]`.
- [x] T012 [US1] Update active workspace `.agents/mcp_config.json` with `"args": ["--root", "c:\\DevDojo\\Buddhi\\buddhi-cli"]`.

**Checkpoint**: `buddhi-mcp` works without `cwd` and `buddhi init` produces correctly configured `mcp_config.json`.

---

## Phase 4: User Story 2 - Add `/ask` Workflow for Codebase Q&A (Priority: P2)

**Goal**: Provide a dedicated codebase Q&A workflow `/ask` that updates the code graph via `buddhi generate` and queries the graph to answer questions with `file:line` citations without editing files.

**Independent Test**:
Verify `.agents/workflows/ask.md` exists and defines Step 1 running `buddhi generate` via `terminal-runner` and Step 2 querying `buddhi_search` and `buddhi_read`.

### Tests for User Story 2

- [x] T013 [P] [US2] Update `tests/test_cli_init.py` to assert that `(agents_dir / "workflows" / "ask.md").exists()`.

### Implementation for User Story 2

- [x] T014 [US2] Create `/ask` workflow template in `src/buddhi/templates/agents/workflows/ask.md`.
- [x] T015 [US2] Scaffold active `/ask` workflow file into `.agents/workflows/ask.md`.
- [x] T016 [US2] Update `src/buddhi/templates/agents/templates/agents-template.md` and repository root `AGENTS.md` to document the `/ask` command.

**Checkpoint**: `/ask` workflow is available in templates and initialized workspaces.

---

## Phase 5: User Story 3 - Pre-Execution `buddhi generate` in Existing Workflows (Priority: P3)

**Goal**: Ensure `/specify`, `/debug`, and `/quick-plan` always run `buddhi generate` as Step 1 to keep the code graph fresh before grounding or reasoning.

**Independent Test**:
Inspect `/specify`, `/debug`, and `/quick-plan` workflow files in both `src/buddhi/templates/agents/workflows/` and `.agents/workflows/` to verify Step 1 executes `buddhi generate` via `terminal-runner`.

### Implementation for User Story 3

- [x] T017 [US3] Update `src/buddhi/templates/agents/workflows/specify.md` to execute `buddhi generate` as Step 1.
- [x] T018 [US3] Update `src/buddhi/templates/agents/workflows/debug.md` to execute `buddhi generate` as Step 1.
- [x] T019 [US3] Update `src/buddhi/templates/agents/workflows/quick-plan.md` to execute `buddhi generate` as Step 1.
- [x] T020 [P] [US3] Update active workspace workflows `.agents/workflows/specify.md`, `.agents/workflows/debug.md`, and `.agents/workflows/quick-plan.md` to reflect the updated Step 1.

**Checkpoint**: All specified workflows update the code graph before execution.

---

## Phase 6: Polish & Verification

**Purpose**: End-to-end verification, linting, and prerequisite validation.

- [x] T021 Run full test suite with `uv run pytest` and verify all tests pass.
- [x] T022 Run code quality checks with `uv run ruff check .` and `uv run mypy src/`.
- [x] T023 Run `uv run buddhi sdd check --json` to verify SDD workflow state and documentation.

---

## Dependencies & Execution Order

- **Phase 1 (Setup)** → **Phase 2 (Foundational)**: Prerequisite before user stories.
- **Phase 3 (User Story 1 - P1)**: Core MVP.
- **Phase 4 (User Story 2 - P2)**: Depends on Phase 2 & 3.
- **Phase 5 (User Story 3 - P3)**: Depends on Phase 2 & 3.
- **Phase 6 (Polish & Verification)**: Runs after all user stories are complete.
