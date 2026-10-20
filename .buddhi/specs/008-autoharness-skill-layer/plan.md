# Implementation Plan: AutoHarness Self-Learning Skill Layer & Scripts for Google Antigravity

**Branch**: `008-autoharness-skill-layer` | **Date**: 2026-10-27 | **Spec**: [.buddhi/specs/008-autoharness-skill-layer/spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/008-autoharness-skill-layer/spec.md)

---

## Summary

Implement the `autoharness` self-learning skill layer adapted from Tigerless Labs' `autoharness` (`v0.5.3`, MIT License) into `buddhi-cli` and the Google Antigravity harness scaffolded by `buddhi init`. 

The implementation delivers:
1. **Zero-Dependency Python Package (`src/buddhi/scripts/autoharness/`)**: Modular engine staying strictly under the 8,000-token ratchet budget (<25 KB per file), providing cross-platform file locking (`msvcrt`/`fcntl`), atomic file writes, regex redaction with Luhn card validation, static safety scanning (6 threat families), a 6-gate deterministic admission validator, atomic promoter, sidecar ownership tracker (`created_by: "agent"`), append-only ledger, and lifecycle graduation/eviction.
2. **Unified CLI Command Group (`buddhi scripts autoharness`)**: Exposes `stage`, `promote`, `validate`, `status`, `capture`, `curate`, `check-links`, and `--selftest` in `src/buddhi/commands/scripts.py`.
3. **FastMCP Integration (`stage_skill`)**: Registers `stage_skill` on `buddhi-mcp` (`src/buddhi/mcp/server.py`) for direct, tool-based staging with immediate schema and front-end validation feedback.
4. **Antigravity Customizations (`src/buddhi/templates/agents/` & `.agents/`)**: Scaffolds the interactive `/learn` skill (`.agents/skills/learn/SKILL.md` + `references/format_spec.md`), always-on rule (`.agents/rules/autoharness.md`), read-only subagents (`.agents/agents/reflector.md` and `curator.md`), and fail-open lifecycle hook (`.agents/hooks/autoharness_hook.py` registered in `hooks.json`).
5. **SDD Integration & Attribution**: Integrates AutoHarness checkpoints into `/implement`, `/verify`, `/close-spec`, and `/status`, and updates `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`.

---

## Technical Context

**Language/Version**: Python >= 3.10 (tested on Python 3.10, 3.11, 3.12).
**Primary Dependencies**: Standard library only for `autoharness` core (`re`, `json`, `dataclasses`, `pathlib`, `ast`, `tempfile`, `hashlib`, `shutil`, `tarfile`, `msvcrt`/`fcntl`). Existing project dependencies for CLI and MCP (`typer`, `rich`, `mcp`). Zero heavy third-party additions.
**Storage**: File-based state in `.agents/skills/` (live skills), `.agents/skills/.archive/` (evicted skills), `.agents/autoharness/intents/` (intent queue), `.agents/autoharness/runs/` (run accounts and `last_run.json`), and `.agents/autoharness/snapshots/` (pre-curation tarballs). Machine-global layer under `~/.gemini/config/` (configurable).
**Testing**: Dual-track: `buddhi scripts autoharness --selftest` (in-tree fixture test runner) and `uv run pytest tests/test_autoharness_*.py` (unit & integration tests).
**Target Platform**: Cross-platform: Windows (with `msvcrt.locking` and reserved device name sanitization) and POSIX (Linux/macOS with `fcntl.flock`).
**Performance Goals**: Hook overhead < 50ms per tool invocation; fast-path atomic file locking; promoter queue drain < 200ms.
**Constraints**: Every source file in `src/buddhi/scripts/autoharness/` MUST be <= 8,000 tokens (tested via `buddhi scripts check-file-size --all`).

---

## AGENTS.md & Harness Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Project build & test commands adhered to (`uv run pytest`, `uv run ruff check .`, `uv run mypy src/ tests/`).
- [x] Architectural constraints respected (stdlib-only core, token ratchet compliance, deterministic static gating).
- [x] No unapproved external dependencies introduced (uses existing `typer`, `rich`, and `mcp`).
- [x] Antigravity customization guidelines honored:
  - Skills use YAML frontmatter (`name`, `description`), progressive disclosure (`references/format_spec.md`), and imperative instructions.
  - Rules use YAML frontmatter (`name`, `trigger: always_on`, `priority: P0`).
  - Subagents specify `subagent: true`, `mainAgent: false`, read-only tools, and `commandExecutionPolicy: sandbox`.
  - Hooks implement the Antigravity camelCase JSON contract (`conversationId`, `workspacePaths`, `transcriptPath`, `toolCall`, `injectSteps`, `decision: "allow"`).

---

## Project Structure

### New Modules (`src/buddhi/scripts/autoharness/`)

```text
src/buddhi/scripts/autoharness/
├── __init__.py                # Package exports, version, and selftest entrypoint
├── models.py                  # Dataclasses: SkillIntent, SidecarData, GateViolation, RunAccount
├── config.py                  # Environment parsing (AUTOHARNESS_*), thresholds, layer paths
├── lock.py                    # Cross-platform advisory file locking (msvcrt on Windows, fcntl on POSIX)
├── atomic.py                  # Atomic text & byte writing via mkstemp + os.replace
├── layer.py                   # Root resolution, git worktree remapping, path & Windows device name checks
├── redact.py                  # Single-pass regex redaction, Luhn credit-card validator, secret_hits()
├── skills_guard.py            # Static regex scanner across 6 threat families (exfiltration, injection, etc.)
├── validate.py                # Deterministic 6-gate admission linter & dependency-free YAML frontmatter parser
├── skill_store.py             # Skill directory CRUD, atomic write, delta patching, archival, orphan sweep
├── sidecar.py                 # .sidecar.json atomic reader/updater (created_by, use, view, patch, anchor)
├── ledger.py                  # Append-only .ledger.jsonl writer/reader with evidence hashing
├── intent_queue.py            # JSONL queue reader/writer for intents/<run_id>.jsonl
├── promoter.py                # Intent queue drainer, validate gatekeeper, atomic lander, and notifier
├── lifecycle.py               # Pure-function evaluator: probation, graduation, capacity eviction
├── metrics.py                 # Read-only status & telemetry collector (rates, funnel, deaths, categories)
├── capture.py                 # Transcript JSONL window slicer + prior-context digester
├── check_doc_links.py         # Markdown relative link validator (skipping .archive/)
└── selftest.py                # Zero-dependency in-tree fixture self-test suite
```

### CLI & MCP Changes

- `src/buddhi/commands/scripts.py`: Add `autoharness_app` subcommand group (`stage`, `promote`, `validate`, `status`, `capture`, `curate`, `check-links`, `--selftest`).
- `src/buddhi/mcp/server.py`: Register `@mcp.tool() def stage_skill(...)`.
- `src/buddhi/commands/init.py`: Sync AutoHarness templates into `.agents/` and ensure hooks are merged.

### Templates & Antigravity Customizations

```text
src/buddhi/templates/agents/
├── rules/
│   └── autoharness.md         # Always-on rule for self-learned skill index, /learn, and reminders
├── skills/
│   ├── learn/
│   │   ├── SKILL.md           # Interactive /learn skill (Compare-First, stage_skill only)
│   │   └── references/
│   │       └── format_spec.md # Format spec for skill authoring & altitude rules
│   ├── implement/SKILL.md     # Updated with AutoHarness procedural checkpoint
│   ├── verify/SKILL.md        # Updated with AutoHarness procedural checkpoint
│   ├── close-spec/SKILL.md    # Updated to distinguish procedural /learn from memory promote
│   └── status/SKILL.md        # Updated to report AutoHarness live skills & funnel
├── agents/
│   ├── reflector.md           # Reflector subagent definition (read-only + stage_skill)
│   └── curator.md             # Curator subagent definition (read-only + stage_skill)
├── hooks/
│   └── autoharness_hook.py    # Fail-open hook script for SessionStart, PreToolUse, Stop
└── hooks.json                 # Registers autoharness_hook.py alongside guard_destructive & graph_context
```

### Tests (`tests/`)

```text
tests/
├── test_autoharness_config.py
├── test_autoharness_redact_and_guard.py
├── test_autoharness_validate.py
├── test_autoharness_promoter_and_store.py
├── test_autoharness_lifecycle.py
├── test_autoharness_hooks.py
├── test_autoharness_mcp.py
└── test_autoharness_cli.py
```

### Documentation

- `ACKNOWLEDGMENTS.md`: Dedicated section for Tigerless Labs `autoharness` with MIT license text.
- `CHANGELOG.md`: Entry under `[Unreleased]`.
- `README.md`: Overview of AutoHarness self-learning capabilities.

---

## Architectural Decision Records (ADRs) & Trade-Offs

### ADR 1: Storage Layer Separation (.agents/skills/ vs .agents/memory/)
- **Context**: `buddhi-cli` already has an OKF v0.2 concept memory layer under `.agents/memory/` for project decisions, conventions, preferences, and SDD rationales.
- **Decision**: Keep procedural "how-to" runbooks, workarounds, and tool guidance in self-learned skills (`.agents/skills/<name>/SKILL.md`), managed by AutoHarness with `.sidecar.json`, `.ledger.jsonl`, and usage-based graduation. Keep architectural decisions, invariants, and rationale in OKF concept notes (`.agents/memory/`).
- **Rationale**: Skills have execution triggers (`description`) and progressive subfiles (`references/`, `scripts/`), making them ideal for operational behavior. OKF memory nodes are declarative and path-scoped.

### ADR 2: Ownership Protection via `.sidecar.json`
- **Context**: An automated agent could mistakenly modify or delete core system skills like `/specify`, `/verify`, or user-authored skills.
- **Decision**: Require `.sidecar.json` with `"created_by": "agent"` for any mutation target. Any skill lacking this is immutable to AutoHarness.
- **Rationale**: Eliminates accidental regressions of human or framework skills.

### ADR 3: Antigravity Subagent Execution Model
- **Context**: Upstream `autoharness` spawned `claude -p --agent reflector` in background subprocesses. In Google Antigravity, subagents are first-class peers invoked via `invoke_subagent`.
- **Decision**: Provide subagent definitions (`.agents/agents/reflector.md` and `curator.md`) for Antigravity's native `invoke_subagent` workflow, while the `Stop` hook notifies the main agent when tool/request thresholds are crossed. Additionally support explicit batch capture and curation via `buddhi scripts autoharness capture` and `curate`.
- **Rationale**: Integrates seamlessly with Antigravity 2.0 and IDE subagent panes without requiring unsupported CLI session fork flags.

---

## Phase Breakdown & Tasks Outline

### Phase 1: Core Foundation & Safety (`src/buddhi/scripts/autoharness/`)
- Implement `models.py`, `config.py`, `lock.py`, `atomic.py`, `layer.py`.
- Implement `redact.py` with Luhn card verification and `secret_hits()`.
- Implement `skills_guard.py` with 6 threat families.
- Implement `validate.py` with custom YAML frontmatter parser and 6-gate admission linter.

### Phase 2: Storage, Promoter, and Lifecycle Engine
- Implement `sidecar.py`, `ledger.py`, `skill_store.py`.
- Implement `intent_queue.py` and `promoter.py` (atomic landing, evidence materialization).
- Implement `lifecycle.py` (probation, graduation, eviction) and `metrics.py`.
- Implement `capture.py` (transcript windowing & digest) and `check_doc_links.py`.
- Implement `selftest.py` covering all subsystems.

### Phase 3: CLI, MCP & Antigravity Hook
- Implement `buddhi scripts autoharness` commands in `src/buddhi/commands/scripts.py`.
- Register `stage_skill` in `src/buddhi/mcp/server.py`.
- Implement `autoharness_hook.py` handling `SessionStart`, `PreToolUse`, `Stop` with Antigravity JSON contracts.

### Phase 4: Templates, Rules, Subagents & SDD Integration
- Create `.agents/rules/autoharness.md`.
- Create `.agents/skills/learn/SKILL.md` and `references/format_spec.md`.
- Create `.agents/agents/reflector.md` and `curator.md`.
- Update `src/buddhi/commands/init.py` to sync AutoHarness templates.
- Update SDD skills: `/implement`, `/verify`, `/close-spec`, `/status`.

### Phase 5: Verification, Tests & Documentation
- Build Pytest test suite (`tests/test_autoharness_*.py`).
- Run `buddhi scripts autoharness --selftest`.
- Run `buddhi scripts check-file-size --all` to verify <= 8,000 tokens per module.
- Run `uv run ruff check .` and `uv run mypy src/ tests/`.
- Update `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`.
