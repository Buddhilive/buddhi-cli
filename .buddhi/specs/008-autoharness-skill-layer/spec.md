# Feature Specification: AutoHarness Self-Learning Skill Layer & Scripts for Google Antigravity

**Feature Branch**: `008-autoharness-skill-layer`

**Created**: 2026-10-27

**Status**: Approved

**Input**: User description: "Analyze the `autoharness` project located in `./temp/autoharness/` and see the licensing of the repo to verify that code and the idea in this repo can be reused without any legal issue. If it is permitted, analyze that project to understand how it is implemented for AI coding assistants. Then implement the `autoharness` skill layer optimizing it for Google Antigravity and existing Spec Driven Development workflow in `buddhi-cli` adhering to the best practices for Antigravity. For scripts, adopt it in Python and integrate it to `buddhi scripts` command workflow."

---

## Licensing & Legal Verification Summary

- **Upstream Repository**: [https://github.com/tigerless-labs/autoharness](https://github.com/tigerless-labs/autoharness) (`v0.5.3`)
- **License**: **MIT License** (`Copyright (c) 2026 ryan` / **Tigerless Labs**)
- **Legal Verdict**: Permitted for full reuse, modification, adaptation, and distribution in `buddhi-cli` without legal issue, subject to preserving the upstream MIT copyright notice and permission notice in `ACKNOWLEDGMENTS.md` (and module docstrings where appropriate).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stage, Validate, and Promote Self-Learned Skills via CLI & MCP (Priority: P1 - MVP)

As an AI coding agent or developer using `buddhi-cli` in Google Antigravity, I want a deterministic, two-stage skill admission pipeline (`stage_skill` MCP tool + `buddhi scripts autoharness` promoter and 6-gate admission validator) that creates, updates, patches, or archives agent-authored skills under `.agents/skills/` (project layer) or `~/.gemini/config/skills/` (global layer), while strictly protecting human/native skills from modification.

**Why this priority**: The core invariant of AutoHarness is safe, self-contained skill authoring with ownership isolation (`.sidecar.json` with `created_by: "agent"`), append-only provenance (`.ledger.jsonl` + content-addressed redacted evidence in `references/evidence-<sha256>.md`), and 6 deterministic validation gates (`safety`, `secret`, `structure`, `files`, `completeness`, `altitude`/`description`). Without this core engine and its CLI/MCP interfaces, neither interactive `/learn` nor automated reflection/curation can safely operate.

**Independent Test**: Can be fully tested by invoking `buddhi scripts autoharness --selftest`, staging skill intents (`create`, `update`, `patch`, `remove_file`, `delete`) via `buddhi scripts autoharness stage` or the `stage_skill` MCP tool, running `buddhi scripts autoharness promote`, and verifying that valid skills land with `.sidecar.json`, `.ledger.jsonl`, and redacted evidence, while invalid or native-skill-targeting intents are deterministically rejected.

**Acceptance Scenarios**:

1. **Given** an initialized workspace with native skills in `.agents/skills/`, **When** an agent calls `stage_skill(action="create", ...)` with a valid class-level skill and runs `buddhi scripts autoharness promote`, **Then** the promoter writes `.agents/skills/<name>/SKILL.md`, `references/evidence-<hash>.md`, `.sidecar.json` (`created_by: "agent"`), and `.ledger.jsonl`.
2. **Given** a native/human-authored skill in `.agents/skills/specify/` (no `.sidecar.json` with `created_by: "agent"`), **When** an agent attempts to `patch`, `update`, `remove_file`, or `delete` that skill, **Then** the promoter rejects the intent with a `self_produced` validation error and leaves the native skill untouched.
3. **Given** a staged skill proposal containing unredacted secrets (e.g., AWS key, GitHub token, PEM private key), dangerous shell patterns (`rm -rf /`, reverse shells, prompt injection), placeholder tokens (`TODO`, `FIXME`), or exceeding the 25-line body altitude cap, **When** `buddhi scripts autoharness validate` or `promote` runs, **Then** the proposal is rejected with structured gate diagnostics in `runs/<run_id>.json` and `last_run.json`.
4. **Given** `buddhi scripts autoharness --selftest` is executed, **Then** all internal unit/fixture self-tests (redaction, Luhn check, safety scanner, frontmatter parser, 6-gate validator, promoter, lifecycle evaluation, link checker) pass with exit code `0`.

---

### User Story 2 - Interactive `/learn` Skill, `reflector` & `curator` Subagents, and Antigravity Rule (Priority: P2)

As a user or primary agent in Google Antigravity, I want an interactive `/learn` skill, an always-on routing rule (`.agents/rules/autoharness.md`), and specialized `reflector` and `curator` subagents (`.agents/agents/reflector.md` and `.agents/agents/curator.md`) so the agent can distill reusable procedural skills from live debugging/coding episodes and periodically consolidate overlapping agent-authored skills into cohesive class-level umbrellas.

**Why this priority**: Provides the agentic intelligence layer optimized for Google Antigravity's native subagent (`invoke_subagent`) and progressive disclosure architecture, enabling both user-directed `/learn` and automated episode reflection/curation.

**Independent Test**: Can be tested by running `buddhi init` on a target directory and verifying that `.agents/skills/learn/SKILL.md` (with `references/format_spec.md`), `.agents/rules/autoharness.md`, `.agents/agents/reflector.md`, and `.agents/agents/curator.md` are scaffolded with valid Antigravity frontmatter and tool permissions (`stage_skill`, `buddhi_read`, `buddhi_search`), and that `buddhi scripts autoharness capture` and `buddhi scripts autoharness curate` generate redacted episode/curation bundles and rotating `.tar.gz` snapshots.

**Acceptance Scenarios**:

1. **Given** a coding session where a non-trivial workaround or user correction occurred, **When** the user invokes `/learn` (or the agent invokes the `reflector` subagent with a captured episode bundle), **Then** the agent follows the Compare-First order (`patch` -> `update` -> `create`), reconciles any contradicted agent skills, and stages the proposal via `stage_skill`.
2. **Given** multiple narrow agent-authored skills in `.agents/skills/`, **When** `buddhi scripts autoharness curate` prepares a pre-curation `.tar.gz` snapshot and the `curator` subagent runs, **Then** overlapping agent skills are merged into a class-level umbrella skill and absorbed skills are archived via `delete(absorbed_into=...)` without touching any native skill.
3. **Given** `buddhi init` is executed in a repository, **Then** `.agents/rules/autoharness.md`, `.agents/skills/learn/`, `.agents/agents/reflector.md`, and `.agents/agents/curator.md` are synced cleanly into `.agents/`.

---

### User Story 3 - Antigravity Lifecycle Hooks & Usage-Driven Graduation/Eviction (Priority: P3)

As a developer working across multiple Antigravity sessions, I want fast, fail-open lifecycle hooks (`.agents/hooks/autoharness_hook.py` registered in `.agents/hooks.json`) that adapt to Antigravity's camelCase stdin/stdout hook contracts (`SessionStart`, `PreToolUse`, `Stop`), automatically track skill usage (`view` and `use`), evaluate probation graduation and capacity eviction on `SessionStart`, inject the categorized recall index of agent-authored skills, and drain staged intents on `Stop`.

**Why this priority**: Closes the self-learning feedback loop automatically across sessions so useful skills survive, unused probation skills (`use == 0` and `view == 0` after maturity threshold) are archived to `.agents/skills/.archive/`, and staged intents land automatically at turn boundaries.

**Independent Test**: Can be tested by piping Antigravity-formatted JSON payloads (`conversationId`, `workspacePaths`, `transcriptPath`, `toolCall`, `terminationReason`) to `python .agents/hooks/autoharness_hook.py` for `SessionStart`, `PreToolUse`, and `Stop` events and verifying the stdout JSON contract (`injectSteps` / `decision` / `reason`) and state updates in `.agents/autoharness/` and `.sidecar.json`.

**Acceptance Scenarios**:

1. **Given** staged intents in `.agents/autoharness/intents/interactive.jsonl`, **When** the `Stop` hook fires with an Antigravity payload, **Then** the hook drains and promotes the queue, writes `last_run.json`, increments the layer request counter, and outputs `{}` (or a reflection/curation notification when thresholds `REFLECT_EVERY_N=50` or `CONSOLIDATE_EVERY_N=250` are crossed).
2. **Given** a `PreToolUse` event where the agent reads a file inside `.agents/skills/<agent-skill>/` (`view_file`, `read_file`, or `buddhi_read`), **When** `autoharness_hook.py` processes the event, **Then** `.sidecar.json` increments `view` (or `use` when `SKILL.md` is activated) and returns `{"decision": "allow"}` in `<50ms`.
3. **Given** a `PreToolUse` event from a read-only `reflector` or `curator` child context attempting to call `write_file` or `edit_file`, **When** `autoharness_hook.py` processes the event, **Then** it returns `{"decision": "deny", "reason": "..."}` enforcing the `stage_skill`-only boundary.
4. **Given** a `SessionStart` event when agent-authored skills exist and `last_run.json` is present, **When** `autoharness_hook.py` runs, **Then** it evaluates `lifecycle.evaluate()` (archiving expired unused probation skills or over-capacity lowest-rate skills), consumes `last_run.json`, and returns `injectSteps` containing the last-run summary and the categorized index of live agent-authored skills.

---

### User Story 4 - Spec-Driven Development (SDD) Integration & Documentation/Acknowledgments (Priority: P4)

As a team using `buddhi-cli`'s Spec-Driven Development workflow (`/specify`, `/spec-plan`, `/implement`, `/verify`, `/close-spec`, `/status`), I want AutoHarness integrated into SDD checkpoints and observability commands, and I want `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md` updated with full attribution to Tigerless Labs' `autoharness`.

**Why this priority**: Aligns the self-learning skill layer with existing SDD workflows so procedural workarounds discovered during `/implement` and `/verify` become reusable skills, while architectural decisions continue flowing to OKF memory during `/close-spec`.

**Independent Test**: Can be verified by checking the updated SDD skill templates (`/implement`, `/verify`, `/close-spec`, `/status`), running `buddhi scripts autoharness status` and `buddhi scripts autoharness check-links`, and verifying `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`.

**Acceptance Scenarios**:

1. **Given** an active SDD cycle in `/implement`, `/verify`, or `/close-spec`, **When** the agent encounters reusable procedural debugging/tooling lessons vs. architectural decisions, **Then** the SDD skills guide the agent to stage procedural runbooks via `stage_skill` (`/learn`) and architectural rationales via `buddhi_memory` (`buddhi memory sdd-promote`).
2. **Given** a user runs `/status` or `buddhi scripts autoharness status [--json]`, **Then** the harness reports live agent-authored skills, usage/view rates, archived skill counts, and promotion funnel metrics (`proposed`, `landed`, `rejected`, `reject_families`).
3. **Given** the completed implementation, **When** inspecting `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`, **Then** `ACKNOWLEDGMENTS.md` includes a dedicated `autoharness` section with link `https://github.com/tigerless-labs/autoharness` and full MIT license text, `CHANGELOG.md` documents the feature under `[Unreleased]`, and `README.md` documents the new capabilities.

---

### Edge Cases

- **Native vs. Agent Skill Collision**: If an agent attempts to `create` a skill whose name already exists as a native skill (either in project `.agents/skills/` or global `~/.gemini/config/skills/`), promotion MUST fail with `already_exists` / `self_produced` without overwriting any files.
- **Malformed Hook Stdin / Missing Transcript**: If `autoharness_hook.py` receives empty stdin, invalid JSON, or a missing `transcriptPath`, it MUST fail open (`{"decision": "allow"}` or `{}`) with exit code `0` and never block the Antigravity agent loop.
- **Windows File Locking & Reserved Names**: File locks (`lock.py`) MUST handle Windows `msvcrt.locking` (`EDEADLOCK` retry) and POSIX `fcntl.flock`. Skill and subfile names MUST reject path traversal (`..`, `/`, `\`), uppercase characters, and Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`).
- **CRLF vs. LF Frontmatter & Block Scalars**: The dependency-free frontmatter parser MUST handle both LF and CRLF line endings as well as YAML literal (`|`) and folded (`>`) block scalars.
- **Ratchet Token Budget**: Every Python module added under `src/buddhi/scripts/autoharness/` MUST stay comfortably below the 8,000-token (`check-file-size`) ceiling.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Package & Ratchet Compliance)**: System MUST implement the `autoharness` Python package under `src/buddhi/scripts/autoharness/` using Python 3.10+ standard library modules, keeping every file under the 8,000-token file-size ratchet limit.
- **FR-002 (Two-Layer Storage Architecture)**: System MUST support `project` (`.agents/skills/` and `.agents/autoharness/`) and `global` (`~/.gemini/config/skills/` and `~/.gemini/config/autoharness/`, configurable via `AUTOHARNESS_DISABLE_GLOBAL`) layers, with git worktree resolution mapping linked worktrees back to the main repository root.
- **FR-003 (Ownership Isolation via `.sidecar.json`)**: System MUST track agent-authored skills via `.sidecar.json` (`created_by: "agent"`, `use`, `view`, `patch`, `reused_gen`, `anchor`, `verification`). The promoter MUST refuse to modify, overwrite, or delete any skill directory lacking `created_by: "agent"`.
- **FR-004 (6-Gate Admission Validator)**: System MUST validate every staged `create`, `update`, and `patch` intent through 6 deterministic gates before landing:
  1. *Safety*: Static regex scan (`skills_guard.py`) across 6 threat families (`exfiltration`, `injection`, `destructive`, `persistence`, `network`, `obfuscation`).
  2. *Secret & PII Redaction*: Single-pass regex + Luhn credit-card scanner (`redact.py`) rejecting unredacted secrets in skill bodies/subfiles and automatically redacting evidence and transcripts.
  3. *Structure & Syntax*: Valid YAML frontmatter (`name`, `description`, `category`), whitelisted subfile directories (`references/`, `templates/`, `scripts/`, `assets/`), bidirectional pointer checks between `SKILL.md` and subfiles, and `ast.parse()` syntax validation for any `.py` subfile.
  4. *File Quotas*: Max 8 subfiles per skill, max 64 KB per subfile, max 256 KB total subfiles, max 100 KB body, and protection against manual overwriting of `references/evidence-*.md`.
  5. *Completeness & Altitude*: No placeholder tokens (`TODO`, `FIXME`, `XXX`), max 25 non-blank body lines (`SKILL_BODY_MAX_LINES`), trigger-first description (`<= 60` chars in index, containing `when` or quoted trigger phrase), and repo-agnostic path check for `global` skills.
  6. *Provenance & Ownership*: Required `reason` and `evidence` fields (materialized to `references/evidence-<sha256>.md` and logged to `.ledger.jsonl`) and `absorbed_into` verification on `delete` when consolidating.
- **FR-005 (`buddhi scripts autoharness` CLI)**: System MUST integrate an `autoharness` command group under `buddhi scripts` providing:
  - `buddhi scripts autoharness stage`: Stage a skill intent (`create`, `update`, `patch`, `remove_file`, `delete`) into the intent queue with immediate front-end validation.
  - `buddhi scripts autoharness promote`: Drain and validate queued intents (`--run-id`, default `interactive`) and write run accounts (`runs/<run_id>.json`, `last_run.json`).
  - `buddhi scripts autoharness validate`: Run the 6-gate admission linter against an existing or candidate skill directory/file.
  - `buddhi scripts autoharness status`: Display or emit JSON (`--json`) observability metrics (`live_symbols`, `use_total`, `view_total`, `requests`, `recall_rate`, `archived_total`, `deaths`, `funnel`, `reject_families`, `by_category`).
  - `buddhi scripts autoharness capture`: Slice and redact a session transcript JSONL from the last byte offset watermark and emit a prior-context digest + episode bundle for the `reflector` subagent.
  - `buddhi scripts autoharness curate`: Create rotating `.tar.gz` skill snapshots (`SNAPSHOT_KEEP=5`) and emit a curation bundle of agent-authored skills for the `curator` subagent.
  - `buddhi scripts autoharness check-links`: Scan markdown documentation/skills for broken relative links (skipping `.archive/`).
  - `buddhi scripts autoharness --selftest`: Run built-in self-tests across all autoharness subsystems.
- **FR-006 (`stage_skill` MCP Tool)**: System MUST register `stage_skill` on the `buddhi-mcp` FastMCP server (`src/buddhi/mcp/server.py`) so main and child agents can stage skill intents directly over MCP with immediate front-end schema and structure feedback.
- **FR-007 (Antigravity Customizations — Skills, Rules, Subagents, Hooks)**:
  - **Skill**: `.agents/skills/learn/SKILL.md` and `.agents/skills/learn/references/format_spec.md` teaching the `/learn` workflow and skill authoring format specification.
  - **Rule**: `.agents/rules/autoharness.md` (`trigger: always_on`) establishing how the agent uses the injected agent-skill recall index, when to use `/learn` (`stage_skill`) vs. `/remember` (`buddhi_memory`), and how to act on reflection/curation reminders.
  - **Subagents**: `.agents/agents/reflector.md` and `.agents/agents/curator.md` configured with Antigravity frontmatter (`subagent: true`, `mainAgent: false`, read-only tools + `stage_skill`).
  - **Hook**: `.agents/hooks/autoharness_hook.py` registered in `.agents/hooks.json` for `SessionStart`, `PreToolUse`, and `Stop`, supporting both Antigravity's camelCase hook contracts (`conversationId`, `workspacePaths`, `transcriptPath`, `toolCall`, `injectSteps`) and Claude/generic fallback fields.
- **FR-008 (SDD Workflow Integration)**: System MUST integrate AutoHarness checkpoints into `/implement`, `/verify`, `/close-spec`, and `/status` templates under `src/buddhi/templates/agents/skills/` and `.agents/skills/`.
- **FR-009 (Documentation & Attribution)**: System MUST update `ACKNOWLEDGMENTS.md` with reference to `https://github.com/tigerless-labs/autoharness` and its MIT license, update `CHANGELOG.md` under `[Unreleased]`, and update `README.md` with the new `autoharness` capabilities.

### Key Entities

- **Skill Intent**: A queued mutation proposal (`action` in `create | update | patch | remove_file | delete`, `layer` in `project | global`, `name`, `body`, `old_string`, `new_string`, `files`, `reason`, `evidence`, `absorbed_into`) stored in `.agents/autoharness/intents/<run_id>.jsonl`.
- **Skill Sidecar (`.sidecar.json`)**: Per-skill JSON metadata tracking ownership (`created_by: "agent"`), usage counters (`use`, `view`, `patch`, `reused_gen`), creation request watermark (`anchor`), and verification metadata.
- **Skill Ledger (`.ledger.jsonl`)**: Per-skill append-only audit log recording every mutation action, timestamp, reason, and content-addressed evidence pointer (`references/evidence-<sha256>.md`).
- **Run Account (`runs/<run_id>.json` & `last_run.json`)**: Execution summary of a promoter drain run recording `landed` skills, `rejected` proposals with failure gate/reason, and optional `spawn_error`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `buddhi scripts autoharness --selftest` passes 100% of built-in test assertions covering redaction, safety scanning, frontmatter parsing, 6-gate validation, atomic promotion, sidecar ownership protection, lifecycle graduation/eviction, and markdown link checking with exit code `0`.
- **SC-002**: `uv run pytest` passes all existing test suites plus comprehensive new unit and integration tests for `autoharness` (`tests/test_autoharness_*.py`) with zero regressions.
- **SC-003**: `buddhi scripts check-file-size --all` passes with every source file under the 8,000-token budget, and `uv run ruff check .` and `uv run mypy src/ tests/` pass with zero errors.
- **SC-004**: Running `buddhi init` scaffolds the new `.agents/rules/autoharness.md`, `.agents/skills/learn/`, `.agents/agents/reflector.md`, `.agents/agents/curator.md`, and `.agents/hooks/autoharness_hook.py` (wired in `.agents/hooks.json`).
- **SC-005**: `ACKNOWLEDGMENTS.md`, `CHANGELOG.md` (`[Unreleased]`), and `README.md` accurately document the AutoHarness integration and MIT license attribution for `https://github.com/tigerless-labs/autoharness`.

---

## Assumptions

- In Google Antigravity, workspace customizations live in `.agents/` (`skills/`, `rules/`, `agents/`, `hooks/`, `hooks.json`), and machine-global customizations live in `~/.gemini/config/` (overridable via `AUTOHARNESS_GLOBAL_ROOT` for isolated testing).
- Procedural multi-step workflows, debugging runbooks, and tool usage recipes belong in self-learned AutoHarness skills (`.agents/skills/<name>/`), while declarative architectural decisions, invariants, and SDD rationales continue to live in OKF v0.2 memory (`.agents/memory/`).
