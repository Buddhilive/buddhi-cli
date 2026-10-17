# Tasks: OKF & Claude Code Memory Layer

**Feature**: `005-okf-claude-memory-layer`
**Input**: Design documents from `.buddhi/specs/005-okf-claude-memory-layer/` (`spec.md`, `plan.md`)
**Prerequisites**: `spec.md` (complete), `plan.md` (complete)

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no conflicting dependencies)
- **[Story]**: Mapped user story (`US1`, `US2`, `US3`, `US4`)
- Exact file paths referenced for all actions

---

## Phase 1: Setup & Environment

**Purpose**: Dependency configuration and package directory layout

- [x] T001 Add `pyyaml>=6.0` dependency to `pyproject.toml` and run `uv sync`
- [x] T002 [P] Create `src/buddhi/memory/` module directory with initial `src/buddhi/memory/__init__.py`
- [x] T003 [P] Create initial test suite placeholders `tests/test_memory_*.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core OKF models, safe YAML frontmatter parser, and security sandboxing required by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement OKF v0.2 data classes and enums (`MemoryNode`, `MemorySource`, `MemoryRelation`, `MemoryKind`, `MemoryStatus`, `MemoryConfidence`, `RelationKind`) in `src/buddhi/memory/models.py`
- [x] T005 [P] Implement safe YAML frontmatter splitting and dumping (`split_frontmatter`, `dump_frontmatter`) with Attested Computation field rejection in `src/buddhi/memory/frontmatter.py`
- [x] T006 [P] Implement security invariants (path traversal sandbox `resolve_and_sandbox_import`, resource anchor parsing `parse_source_resource`, slug sanitization `sanitize_slug`, secret leakage scanner `assert_no_secrets_in_tracked_memory`) in `src/buddhi/memory/security.py`
- [x] T007 Implement unit tests for models, frontmatter parsing, and security invariants in `tests/test_memory_model.py` and `tests/test_memory_security.py`
- [x] T008 [P] Update `.gitignore` generation logic in `src/buddhi/util/fsutil.py` to ensure `.agents/memory.local/` and `.agents/agent-memory-local/` are gitignored

**Checkpoint**: Foundation ready — core models, serialization, and security sandboxing verified by test suite.

---

## Phase 3: User Story 1 - Hybrid OKF Memory Bundle, CLI Engine & Legacy Migration (Priority: P1) 🎯 MVP

**Goal**: Deliver a standalone, fully functional OKF v0.2 + Claude Code memory bundle engine, budget-enforced `MEMORY.md` index generator, `buddhi memory` Typer CLI, and legacy flat-file migration during `buddhi init`.

**Independent Test**: Can be verified by running `uv run buddhi memory add`, `status`, `search`, `read`, `validate`, `sync`, `compact`, and `migrate` on a sample workspace with legacy flat memory files and asserting deterministic OKF bundle creation, `<200 lines / 25KB` cap enforcement, and zero data loss.

### Tests for User Story 1
- [x] T009 [P] [US1] Unit tests for SHA-256 line-slicing and staleness detection in `tests/test_memory_provenance.py`
- [x] T010 [P] [US1] Unit tests for `MEMORY.md` 200-line / 25KB budget validator and compaction algorithm in `tests/test_memory_budget.py`
- [x] T011 [P] [US1] Unit tests for legacy flat-file migration and idempotency in `tests/test_memory_migration.py`
- [x] T012 [P] [US1] Integration tests for `buddhi memory` Typer CLI commands in `tests/test_memory_cli.py`

### Implementation for User Story 1
- [x] T013 [P] [US1] Implement line-slicing `#L<start>-L<end>`, CRLF->LF normalization, and SHA-256 staleness checking (`compute_content_hash`, `verify_source_staleness`) in `src/buddhi/memory/hash.py`
- [x] T014 [US1] Implement multi-scope bundle store, budget status checker, `sync_indexes()`, `compact()`, and `log.md` mutation writer in `src/buddhi/memory/store.py`
- [x] T015 [US1] Implement legacy flat-file migration engine (`migrate_legacy_memory`) converting legacy unformatted files into OKF topic nodes and renaming to `.md.bak` in `src/buddhi/memory/migrate.py`
- [x] T016 [US1] Implement `buddhi memory` Typer CLI command group (`status`, `add`, `search`, `read`, `validate`, `sync`, `compact`, `migrate`) in `src/buddhi/commands/memory.py`
- [x] T017 [US1] Mount `memory_app` on root Typer CLI in `src/buddhi/cli.py`
- [x] T018 [US1] Wire `migrate_legacy_memory()` and memory bundle verification into `buddhi init` in `src/buddhi/commands/init.py`
- [x] T019 [US1] Update scaffolded template files in `src/buddhi/templates/agents/memory/` (`MEMORY.md` with `okf_version: "0.2"`, `log.md`, topic `index.md` files)

**Checkpoint**: User Story 1 (MVP) is fully functional and independently testable via `buddhi memory` CLI and `buddhi init`.

---

## Phase 4: User Story 2 - `buddhi_memory` MCP Tool, Path-Scoped Filtering & `@path` Expansion (Priority: P2)

**Goal**: Expose deterministic memory retrieval, active file path glob matching, `@path` import recursion (depth <= 5), and memory persistence directly to AI coding agents via `buddhi-mcp`.

**Independent Test**: Can be verified via FastMCP integration tests executing `buddhi_memory(action="search" | "read" | "remember" | "status")` verifying path-glob matching against active files, sandboxed `@path` inline expansion up to 5 hops with cycle detection, and tool-driven memory creation.

### Tests for User Story 2
- [x] T020 [P] [US2] Unit tests for glob pattern matching (`paths`) and safe `@path` 5-hop import expansion with cycle and sandbox checks in `tests/test_memory_imports.py`
- [x] T021 [P] [US2] Integration tests for `buddhi_memory` tool over FastMCP in `tests/test_memory_mcp.py`

### Implementation for User Story 2
- [x] T022 [US2] Implement active file glob matching (`matches_active_files`) and recursive `@path` import resolver (`resolve_imports`) with 5-hop depth cap and circular loop guard in `src/buddhi/memory/resolver.py`
- [x] T023 [US2] Implement `execute_buddhi_memory` MCP tool controller supporting `search`, `read`, `remember`, `status`, and `promote_sdd` in `src/buddhi/mcp/tools/memory.py`
- [x] T024 [US2] Register `buddhi_memory` tool on FastMCP server instance in `src/buddhi/mcp/server.py`
- [x] T025 [US2] Update `buddhi memory search` and `buddhi memory read` in `src/buddhi/commands/memory.py` to expose `--active-file` and `--expand-imports` using `resolver.py`

**Checkpoint**: User Story 2 is fully functional; AI agents can query path-scoped memories and persist learnings over MCP.

---

## Phase 5: User Story 3 - End-to-End SDD Lifecycle & Subagent Memory Integration (Priority: P2)

**Goal**: Deeply integrate the OKF memory layer into all SDD lifecycle skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`, `/close-spec`), provide dedicated `/memory` skill, and equip domain specialist subagents with persistent memory scopes.

**Independent Test**: Can be verified by running `buddhi memory sdd-promote` on a test spec directory and verifying extraction of `sdd-rationale` and `decision` nodes, plus inspecting updated skills and agent templates.

### Tests for User Story 3
- [x] T026 [P] [US3] Unit and integration tests for SDD promotion engine (`promote_sdd_artifacts`) in `tests/test_memory_sdd_promote.py`

### Implementation for User Story 3
- [x] T027 [US3] Implement SDD promotion engine extracting durable decisions from `plan.md` and verified `sound` choices from `choices.md` into OKF concept nodes in `src/buddhi/memory/sdd_promote.py`
- [x] T028 [US3] Add `buddhi memory sdd-promote [--branch <branch>]` subcommand in `src/buddhi/commands/memory.py`
- [x] T029 [P] [US3] Create new `/memory` agent skill in `src/buddhi/templates/agents/skills/memory/SKILL.md` and `.agents/skills/memory/SKILL.md`
- [x] T030 [P] [US3] Upgrade `/remember` skill to use OKF memory schema and CLI/MCP tools in `src/buddhi/templates/agents/skills/remember/SKILL.md` and `.agents/skills/remember/SKILL.md`
- [x] T031 [P] [US3] Upgrade `/status` skill to report memory budget utilization and staleness counts in `src/buddhi/templates/agents/skills/status/SKILL.md` and `.agents/skills/status/SKILL.md`
- [x] T032 [US3] Update SDD skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`, `/close-spec`) in `src/buddhi/templates/agents/skills/` and `.agents/skills/` to consult `buddhi_memory` and run promotion on close
- [x] T033 [P] [US3] Update specialist subagent definitions in `src/buddhi/templates/agents/agents/` and `.agents/agents/` with `memory: project` frontmatter and domain memory instructions
- [x] T034 [P] [US3] Update harness rules `harness-core.md` and `okf-docs.md` in `src/buddhi/templates/agents/rules/` and `.agents/rules/`

**Checkpoint**: User Story 3 is complete; SDD workflow and specialist subagents actively read and write OKF memory.

---

## Phase 6: User Story 4 - Documentation, Changelog & Acknowledgments Updates (Priority: P3)

**Goal**: Document the new OKF + Claude Code memory layer across project documentation and formalize upstream open-source attributions.

**Independent Test**: Can be verified by inspecting `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, and `README.md` for complete coverage of `buddhi memory`, `buddhi_memory`, bundle structure, and attribution sections.

### Implementation for User Story 4
- [x] T035 [US4] Update `CHANGELOG.md` under `## [Unreleased]` with comprehensive entries for OKF v0.2 + Claude Code memory bundle, `buddhi memory` CLI, `buddhi_memory` MCP tool, and SDD integration
- [x] T036 [US4] Update `ACKNOWLEDGMENTS.md` with structured attribution sections and licenses for Claude Code Memory (`https://code.claude.com/docs/en/memory`) and Google Open Knowledge Format (`https://github.com/GoogleCloudPlatform/open-knowledge-format`, Apache-2.0)
- [x] T037 [US4] Update `README.md` documenting `buddhi memory` CLI commands, `buddhi_memory` MCP tool, `.agents/memory/` bundle architecture, and updated skills

---

## Phase 7: Polish & Verification Gate

**Purpose**: Full regression testing, dogfooding, and code quality verification

- [x] T038 Migrate repository's own `.agents/memory/` using the new `buddhi memory migrate` engine to dogfood the OKF memory bundle
- [x] T039 Execute full test suite via `terminal-runner` (`uv run pytest`) and verify 100% pass rate
- [x] T040 Execute linting and formatting gates (`uv run ruff check .` and `uv run ruff format --check .`)
- [x] T041 Execute static typechecker gate (`uv run mypy src/ tests/`)
- [x] T042 Run `buddhi memory validate` on the workspace to verify 0 budget violations and 0 stale nodes
