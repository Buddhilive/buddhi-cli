# Tasks: AutoHarness Self-Learning Skill Layer & Scripts for Google Antigravity

**Branch**: `008-autoharness-skill-layer` | **Date**: 2026-10-27 | **Spec**: [.buddhi/specs/008-autoharness-skill-layer/spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/008-autoharness-skill-layer/spec.md) | **Plan**: [.buddhi/specs/008-autoharness-skill-layer/plan.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/008-autoharness-skill-layer/plan.md)

---

## Task Organization & Priority Phasing

- **Phase 1: Setup & Core Safety Infrastructure** (Blocking): Foundational packages, configuration, atomic operations, cross-platform locking, redaction with Luhn validation, and static safety scanning.
- **Phase 2: User Story 1 (P1 🎯 MVP) — Admission Validator, Storage & Promotion Engine**: 6-gate admission linter, sidecar ownership barrier (`created_by: "agent"`), append-only ledger, intent queue, promoter, `buddhi scripts autoharness` CLI commands (`stage`, `promote`, `validate`, `status`, `check-links`, `--selftest`), and `stage_skill` MCP tool.
- **Phase 3: User Story 2 (P2) — Interactive `/learn` Skill, `reflector` & `curator` Subagents, and Antigravity Rule**: Scaffolding `.agents/skills/learn/` (with `references/format_spec.md`), `.agents/rules/autoharness.md`, `.agents/agents/reflector.md`, and `.agents/agents/curator.md` via `buddhi init`, plus `capture` and `curate` CLI commands.
- **Phase 4: User Story 3 (P3) — Antigravity Lifecycle Hooks & Usage-Driven Graduation/Eviction**: Implementing `autoharness_hook.py` registered in `.agents/hooks.json` for `SessionStart` (probation/eviction evaluation, last-run consumption, recall index injection), `PreToolUse` (usage & view tracking, child write guard), and `Stop` (intent draining & reflection reminders).
- **Phase 5: User Story 4 (P4) — Spec-Driven Development (SDD) Integration, Polish, Attribution & Verification**: Updating SDD skills (`/implement`, `/verify`, `/close-spec`, `/status`), updating `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`, executing in-tree self-tests, pytest suite, and token ratchet verification.

---

## Tasks

### Phase 1: Setup & Core Safety Infrastructure

- [x] T001 [P] Create package directory `src/buddhi/scripts/autoharness/` and `src/buddhi/scripts/autoharness/__init__.py`.
- [x] T002 [P] Implement core models and dataclasses in `src/buddhi/scripts/autoharness/models.py` (`SkillIntent`, `SidecarData`, `GateFinding`, `ValidationResult`, `RunAccount`, `LifecycleDecision`).
- [x] T003 [P] Implement environment configuration and directory resolution in `src/buddhi/scripts/autoharness/config.py` (`AUTOHARNESS_*` parsing, layer path defaults, worktree discovery).
- [x] T004 [P] Implement cross-platform advisory file locking with timeout context manager in `src/buddhi/scripts/autoharness/lock.py` (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX).
- [x] T005 [P] Implement atomic file writing utilities in `src/buddhi/scripts/autoharness/atomic.py` (`atomic_write_text`, `atomic_write_bytes` using `tempfile.mkstemp` and `os.replace`).
- [x] T006 [P] Implement path validation, worktree remapping, and Windows reserved device name guards in `src/buddhi/scripts/autoharness/layer.py` (`check_new_name`, `check_subfile_path`, `resolve_layer_root`).
- [x] T007 Implement regex secrets & PII redaction engine with Luhn credit-card verification and `secret_hits()` scanner in `src/buddhi/scripts/autoharness/redact.py`.
- [x] T008 Implement static AST & pattern security scanner across 6 threat families (`exfiltration`, `injection`, `destructive`, `persistence`, `network`, `obfuscation`) in `src/buddhi/scripts/autoharness/skills_guard.py`.

---

### Phase 2: User Story 1 (P1 🎯 MVP) — Admission Validator, Storage & Promotion Engine

- [x] T009 [US1] Implement dependency-free YAML frontmatter parser (supporting CRLF and folded/literal block scalars) and the 6-gate deterministic admission validator in `src/buddhi/scripts/autoharness/validate.py`.
- [x] T010 [US1] Implement `.sidecar.json` reader, writer, and atomic counter bump utilities in `src/buddhi/scripts/autoharness/sidecar.py` (`created_by: "agent"` barrier, `use`, `view`, `patch`, `reused_gen`, `anchor`).
- [x] T011 [US1] Implement append-only `.ledger.jsonl` writer and reader with content-addressed evidence hashing in `src/buddhi/scripts/autoharness/ledger.py`.
- [x] T012 [US1] Implement skill directory CRUD, delta patching, atomic landing, and archival in `src/buddhi/scripts/autoharness/skill_store.py`.
- [x] T013 [US1] Implement file-locked JSONL intent queue reader, writer, and cleaner in `src/buddhi/scripts/autoharness/intent_queue.py` (`intents/<run_id>.jsonl`).
- [x] T014 [US1] Implement promoter draining, gatekeeper validation, atomic file and evidence landing, and run accounting in `src/buddhi/scripts/autoharness/promoter.py` (`runs/<run_id>.json`, `last_run.json`).
- [x] T015 [US1] Implement markdown relative link validator (skipping `.archive/`) in `src/buddhi/scripts/autoharness/check_doc_links.py`.
- [x] T016 [US1] Implement zero-dependency in-tree self-test suite covering redaction, safety, frontmatter, 6 gates, sidecar barriers, and promoter in `src/buddhi/scripts/autoharness/selftest.py`.
- [x] T017 [US1] Register `stage_skill` MCP tool with parameter schema and immediate validation on `buddhi-mcp` in `src/buddhi/mcp/server.py`.
- [x] T018 [US1] Add `autoharness` Typer command group (`stage`, `promote`, `validate`, `status`, `check-links`, `--selftest`) to `src/buddhi/commands/scripts.py`.
- [x] T019 [US1] Create unit tests in `tests/test_autoharness_config.py`, `tests/test_autoharness_redact_and_guard.py`, `tests/test_autoharness_validate.py`, and `tests/test_autoharness_promoter_and_store.py`.
- [x] T020 [US1] Checkpoint: Run `buddhi scripts autoharness --selftest` and pytest for US1 to verify P1 MVP passes completely.

---

### Phase 3: User Story 2 (P2) — Interactive `/learn` Skill, `reflector` & `curator` Subagents, and Antigravity Rule

- [x] T021 [US2] Create format specification document `src/buddhi/templates/agents/skills/learn/references/format_spec.md` with altitude and frontmatter authoring rules.
- [x] T022 [US2] Create interactive `/learn` skill `src/buddhi/templates/agents/skills/learn/SKILL.md` instructing the agent on Compare-First order and staging via `stage_skill`.
- [x] T023 [US2] Create read-only reflector subagent definition `src/buddhi/templates/agents/agents/reflector.md` (`subagent: true`, `mainAgent: false`, tools: read-only + `stage_skill`).
- [x] T024 [US2] Create read-only curator subagent definition `src/buddhi/templates/agents/agents/curator.md` (`subagent: true`, `mainAgent: false`, tools: read-only + `stage_skill`).
- [x] T025 [US2] Create always-on Antigravity rule `src/buddhi/templates/agents/rules/autoharness.md` (`trigger: always_on`, `priority: P0`) governing recall index use, `/learn` vs `/remember`, and reminders.
- [x] T026 [US2] Implement transcript window slicing and context digester in `src/buddhi/scripts/autoharness/capture.py`.
- [x] T027 [US2] Add `capture` and `curate` subcommands (generating pre-curation `.tar.gz` snapshots under `snapshots/`) to `src/buddhi/commands/scripts.py`.
- [x] T028 [US2] Update `src/buddhi/commands/init.py` to sync `learn`, `reflector`, `curator`, and `autoharness.md` into target `.agents/`.
- [x] T029 [US2] Create tests for `/learn`, subagent definitions, and template scaffolding in `tests/test_autoharness_init_scaffold.py`.
- [x] T030 [US2] Checkpoint: Verify `buddhi init` scaffolds all new skills, rules, and subagents cleanly without overwriting native files.

---

### Phase 4: User Story 3 (P3) — Antigravity Lifecycle Hooks & Usage-Driven Graduation/Eviction

- [x] T031 [US3] Implement pure-function lifecycle evaluation (probation tracking, graduation retention, capacity eviction) and telemetry metrics in `src/buddhi/scripts/autoharness/lifecycle.py` and `metrics.py`.
- [x] T032 [US3] Implement Antigravity fail-open hook script `src/buddhi/templates/agents/hooks/autoharness_hook.py` supporting `SessionStart` (evaluating lifecycle, consuming `last_run.json`, injecting recall index), `PreToolUse` (bumping `use`/`view`, denying child writes), and `Stop` (draining `interactive.jsonl`, threshold notices).
- [x] T033 [US3] Update `src/buddhi/templates/agents/hooks.json` and `.agents/hooks.json` to register `autoharness_hook.py` alongside `guard_destructive.py` and `graph_context.py`.
- [x] T034 [US3] Sync `autoharness_hook.py` to active `.agents/hooks/autoharness_hook.py`.
- [x] T035 [US3] Create hook contract unit tests in `tests/test_autoharness_hooks.py` and lifecycle tests in `tests/test_autoharness_lifecycle.py`.
- [x] T036 [US3] Checkpoint: Verify hook handles mock Antigravity payloads in `<50ms`, enforces child write blocks, and drains interactive intents on Stop.

---

### Phase 5: User Story 4 (P4) — SDD Integration, Polish, Attribution & Verification

- [x] T037 [US4] Update SDD skill templates in `src/buddhi/templates/agents/skills/` and active `.agents/skills/`:
  - `implement/SKILL.md`: add AutoHarness procedural checkpoint for capturing reusable workarounds.
  - `verify/SKILL.md`: add procedural verification checkpoint.
  - `close-spec/SKILL.md`: clarify distinction between procedural skill learning (`/learn`) and architectural OKF memory promotion (`buddhi memory sdd-promote`).
  - `status/SKILL.md`: include AutoHarness live skills and funnel telemetry in dashboard.
- [x] T038 [US4] Add comprehensive CLI test suite in `tests/test_autoharness_cli.py` and MCP integration tests in `tests/test_autoharness_mcp.py`.
- [x] T039 [US4] Update `ACKNOWLEDGMENTS.md` with dedicated section for `https://github.com/tigerless-labs/autoharness` and upstream MIT license text.
- [x] T040 [US4] Update `CHANGELOG.md` documenting the AutoHarness self-learning skill layer under `[Unreleased]`.
- [x] T041 [US4] Update `README.md` documenting `buddhi scripts autoharness`, `stage_skill`, and self-learning capabilities.
- [x] T042 [US4] Run token ratchet verification `uv run buddhi scripts check-file-size --all` ensuring all new files are strictly `<= 8,000` tokens.
- [x] T043 [US4] Run code quality gates `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src/ tests/`.
- [x] T044 [US4] Run full regression test suite `uv run pytest` ensuring 100% pass across all tests.

