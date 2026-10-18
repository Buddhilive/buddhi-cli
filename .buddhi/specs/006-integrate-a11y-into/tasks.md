# Tasks: Integrate A11Y.md into Antigravity Harness and Spec-Driven Workflow

**Input**: Design documents from `/.buddhi/specs/006-integrate-a11y-into/` (`spec.md`, `plan.md`)  
**Prerequisites**: `spec.md` (complete), `plan.md` (complete)

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Target user story (`US1`, `US2`, `US3`, `US4`)
- Exact file paths are specified for every task

---

## Phase 1: Setup & Scaffolding Packaging

**Purpose**: Prepare directory structure and scaffold the A11Y rules, core skill, 31 reference guides, and 4 governance templates.

- [x] T001 [P] [US1] Create directory structure for templates: `src/buddhi/templates/agents/skills/a11y/references/` and `src/buddhi/templates/agents/skills/a11y/templates/`
- [x] T002 [P] [US1] Copy and adapt 31 reference guides from `temp/A11Y.md/docs/en/references/guide-*.md` to `src/buddhi/templates/agents/skills/a11y/references/`
- [x] T003 [P] [US1] Copy and adapt 4 governance templates (`REPORT.md`, `EXCEPTIONS.md`, `A11Y-DECISIONS.md`, `ACCESSIBILITY.md`) from `temp/A11Y.md/docs/en/templates/` to `src/buddhi/templates/agents/skills/a11y/templates/`
- [x] T004 [US1] Author the adapted core skill `src/buddhi/templates/agents/skills/a11y/SKILL.md` (customized with Antigravity tool guidance, `buddhi scripts`, and MCP integration)
- [x] T005 [P] [US1] Create the always-on Antigravity routing rule `src/buddhi/templates/agents/rules/a11y.md`
- [x] T006 [US1] Sync new templates into project `.agents/` harness and add integration test `tests/test_cli_init_a11y.py` verifying idempotent scaffolding with `buddhi init`

**Checkpoint**: `uv run pytest tests/test_cli_init_a11y.py` passes and `.agents/skills/a11y/` is cleanly scaffolded.

---

## Phase 2: User Story 2 (P2) - Deterministic Verification & Contrast Engine

**Purpose**: Build modular pure-Python static gate (`buddhi scripts verify-a11y`) adhering to the 8,000-token ratchet ceiling, and extend `buddhi scripts contrast`.

- [x] T007 [P] [US2] Implement dataclasses and contracts in `src/buddhi/scripts/verify_a11y/models.py` (`VerifyA11yResult`, `GateFinding`, `ArtifactPaths`)
- [x] T008 [P] [US2] Implement artifact discovery, freshness, status, independence, and exceptions checks in `src/buddhi/scripts/verify_a11y/artifacts.py`
- [x] T009 [P] [US2] Implement 11 source anti-pattern checks and register suppressions in `src/buddhi/scripts/verify_a11y/antipatterns.py`
- [x] T010 [P] [US2] Implement 17 component signatures and contrast table recomputation in `src/buddhi/scripts/verify_a11y/coverage.py`
- [x] T011 [US2] Implement 31 fixture test cases in `src/buddhi/scripts/verify_a11y/selftest.py` and package entrypoint in `src/buddhi/scripts/verify_a11y/__init__.py`
- [x] T012 [US2] Enhance `src/buddhi/scripts/contrast.py` with multi-pair mode (`--bg`, `--fg`, `--profile`), CSS triage mode (`--css`, `--page-bg`), RGBA/HSLA alpha compositing, and `--self-test` fixtures while preserving backward compatibility
- [x] T013 [US2] Wire CLI subcommands `buddhi scripts verify-a11y` and updated `buddhi scripts contrast` in `src/buddhi/commands/scripts.py`
- [x] T014 [US2] Add unit and CLI test suite `tests/test_scripts_verify_a11y.py` and update `tests/test_scripts_contrast.py`

**Checkpoint**: `uv run buddhi scripts verify-a11y --selftest` and `uv run buddhi scripts contrast --selftest` pass with exit code `0`.

---

## Phase 3: FastMCP Tools & SDD Memory Promotion

**Purpose**: Expose A11Y tools to AI agents via FastMCP and promote `A11Y-DECISIONS.md` into OKF memory.

- [x] T015 [P] [US2] Implement `verify_a11y` MCP tool handler in `src/buddhi/mcp/tools/a11y.py` and register on `src/buddhi/mcp/server.py`
- [x] T016 [P] [US2] Extend `check_contrast` MCP tool handler in `src/buddhi/mcp/tools/contrast.py` and `src/buddhi/mcp/server.py` to support `profile`, `bg`, `fg`, and `page_bg`
- [x] T017 [US3] Add `extract_a11y_decisions` to `src/buddhi/memory/sdd_promote.py` and update `promote_sdd_artifacts` to promote `A11Y-DECISIONS.md` to `mem-decision-a11y-*` OKF nodes
- [x] T018 [US2] Add FastMCP unit tests in `tests/test_mcp_a11y.py` and memory promotion tests in `tests/test_memory_sdd_promote_a11y.py`

**Checkpoint**: `uv run pytest tests/test_mcp_a11y.py tests/test_memory_sdd_promote_a11y.py` passes.

---

## Phase 4: User Story 3 (P3) - SDD Workflow & Subagent Integration

**Purpose**: Update SDD lifecycle skills and specialist subagents to integrate A11Y compliance profiles, lazy reference loading, and fresh-context verification.

- [x] T019 [P] [US3] Update `src/buddhi/templates/agents/agents/frontend-specialist.md` with A11Y component reuse, decision queries, and §2.1 guide mapping
- [x] T020 [P] [US3] Update `src/buddhi/templates/agents/skills/specify/SKILL.md` with Compliance Profile prompting and A11Y acceptance criteria
- [x] T021 [P] [US3] Update `src/buddhi/templates/agents/skills/spec-plan/SKILL.md` with component reuse checks and §2.1 reference guide mapping in `plan.md`
- [x] T022 [P] [US3] Update `src/buddhi/templates/agents/skills/spec-tasks/SKILL.md` to tag component tasks with §2.1 reference guides and A11Y governance tasks
- [x] T023 [P] [US3] Update `src/buddhi/templates/agents/skills/implement/SKILL.md` with Image/Media evidence capture and static gate checks
- [x] T024 [P] [US3] Update `src/buddhi/templates/agents/skills/verify/SKILL.md` to execute `buddhi scripts verify-a11y` and dispatch unprimed subagents for Section 7 independent audits
- [x] T025 [P] [US3] Update `src/buddhi/templates/agents/skills/close-spec/SKILL.md` to promote `A11Y-DECISIONS.md` into OKF memory and prompt `ACCESSIBILITY.md` drafting
- [x] T026 [US3] Sync updated template skills and agents into active project harness (`.agents/`)

**Checkpoint**: Verify all updated skills and agent templates parse cleanly and contain proper frontmatter and instructions.

---

## Phase 5: User Story 4 (P4) - Attribution, Changelog & Documentation Updates

**Purpose**: Update documentation, attribution, and changelog per user request.

- [x] T027 [US4] Update `ACKNOWLEDGMENTS.md` with dedicated section and full MIT license text for `fecarrico/A11Y.md` (`https://github.com/fecarrico/A11Y.md`)
- [x] T028 [US4] Update `CHANGELOG.md` under `## [Unreleased]` documenting the `A11Y.md` integration (skills, rules, CLI scripts, MCP tools, SDD workflow, OKF promotion)
- [x] T029 [US4] Update `README.md` to reflect the new `a11y` skill, CLI scripts (`verify-a11y`, `contrast`), and MCP tools

---

## Phase 6: Polish, Ratchet & End-to-End Verification

**Purpose**: Run the full verification suite across formatting, types, tests, and token ratchet.

- [x] T030 Run `uv run ruff check .` and `uv run ruff format --check .`
- [x] T031 Run `uv run mypy src/ tests/`
- [x] T032 Run `uv run buddhi scripts check-file-size --all` to verify no source or test file breaches the 8,000-token threshold
- [x] T033 Run `uv run pytest` across the entire project test suite

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: Unblocks Phases 2, 3, and 4.
- **Phase 2 (Static Gate & Contrast Engine)**: Unblocks Phase 3 (MCP integration).
- **Phase 3 (MCP & Memory Promotion)**: Can proceed alongside Phase 4.
- **Phase 4 (SDD & Specialist Integration)**: Enriches workflow.
- **Phase 5 (Docs & Attribution)**: Completed with full MIT license text.
- **Phase 6 (Polish & Verification)**: All gates green (193/193 tests passed).
