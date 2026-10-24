# Feature Specification: Token-Saving Command Output Filter (`buddhi scripts rtk`)

**Feature Branch**: `010-rtk-style-token`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Analyze rtk (Rust Token Killer, `./temp/rtk/`), check license, assess a Python port, and if feasible implement a new buddhi-cli command that complements the SDD workflow and works well with Antigravity; then update ACKNOWLEDGMENTS.md, README.md, CHANGELOG.md (Unreleased)."

## Upstream Analysis & License Finding

**rtk** v0.49.0 is a CLI proxy that runs a dev command, filters/compresses its output (stats, grouping, dedup, truncation, failure-only), and returns a short result to the LLM. It also ships a hook layer that rewrites `git status` → `rtk git status`, including a Google Antigravity plugin (`plugins/rtk/` with `hooks.json`, rules).

**License (verified from `temp/rtk/LICENSE`, `Cargo.toml`, `README.md`)**: dual-scope.

| Component | License | Reuse in buddhi-cli |
|---|---|---|
| `src/` hooks and command filters, `src/filters/*.json` | Apache-2.0 | **Yes**: concepts and ported filter data allowed with attribution, license text, and a statement of changes (Apache §4) |
| `engine/` (compression engine), `proxy/` (API traffic proxy) | **BUSL-1.1** (source-available, not open source) | **No**: not read, ported, or derived from. Out of scope |

Concepts and ideas are not copyrightable. Python code is written independently. Any ported Apache-2.0 filter data (TOML) keeps its notice and is marked as modified. `ACKNOWLEDGMENTS.md` records Apache-2.0 text and the BUSL exclusion.

**Feasibility**: Feasible in Python. rtk's value is regex/line-based filtering plus a command-rewrite hook, which are I/O-bound and not performance-critical. Rust-specific parts (single static binary, SQLite tracking, per-agent installers for 12 agents) are replaced by `subprocess`, the stdlib, JSON-lines tracking, and an Antigravity-only hook. buddhi-cli already has `scripts/` subcommands, `.agents/hooks.json`, and a fail-open hook pattern (autoharness) to follow.

## Clarifications (Session 2026-10-29)

- Q: Integration surface? → A: `buddhi scripts rtk` (run / filter / gain / rewrite) plus a fail-open Antigravity hook that rewrites noisy commands, a rule, and a skill; SDD `/verify` and `terminal-runner` use it.
- Q: Filter coverage? → A: Broad port of rtk's ~60 TOML filters across languages.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a command with compressed output (Priority: P1)

A developer or agent runs `buddhi scripts rtk run -- <command>`. The command executes, its exit code is preserved, and the output printed is a filtered version (noise, progress bars, passing tests, and repeated lines removed; errors and summaries kept).

**Why this priority**: The standalone engine and filter set is the MVP. Everything else builds on it.

**Independent Test**: Run on fixture outputs for `git status`, `pytest`, `ruff`, and a generic noisy command. Compare token counts and check that all failure lines survive.

**Acceptance Scenarios**:

1. **Given** a command with a matching TOML filter, **When** `rtk run` executes it, **Then** output is reduced per the filter and the exit code equals the original's.
2. **Given** a command with no filter, **When** run, **Then** a generic fallback (ANSI strip, blank-line collapse, duplicate collapse, head/tail truncation with a "N lines omitted" marker) applies.
3. **Given** a failing command, **When** run, **Then** errors are never dropped and the full raw output is saved to a recovery file whose path is printed (tee-on-failure).
4. **Given** a filter that raises or matches nothing, **When** run, **Then** raw output passes through unchanged (fail-open).

---

### User Story 2 - Automatic rewrite via Antigravity hook (Priority: P2)

A `PreToolUse` hook in `.agents/hooks.json` rewrites supported shell commands the agent issues so they route through `buddhi scripts rtk run`, with no user action.

**Why this priority**: This delivers the transparent savings. It needs US1.

**Independent Test**: Feed hook JSON for supported, unsupported, piped, and already-wrapped commands. Assert the rewrite decisions.

**Acceptance Scenarios**:

1. **Given** `git log`, **When** the hook fires, **Then** the command is rewritten to the wrapped form.
2. **Given** a pipe, redirect, heredoc, compound command, or an already-wrapped command, **When** the hook fires, **Then** it is left untouched.
3. **Given** any internal hook error, **When** it fires, **Then** it exits allowing the original command (fail-open), consistent with `guard_destructive.py` and the `CONFIRMED` marker rules.
4. **Given** a command the existing destructive guard denies, **When** both hooks run, **Then** the guard verdict still wins.

---

### User Story 3 - SDD workflow integration (Priority: P2)

`/verify`, `terminal-runner`, `/implement`, and `/debug` skills and agents use the filter for build/lint/test commands. Their evidence reports note the raw vs. filtered size and where the raw log is saved, so "no-bluff" evidence stays auditable.

**Why this priority**: This is the stated goal of complementing SDD. Evidence must stay verifiable after compression.

**Independent Test**: Run `/verify` on a sample failing test. The report shows the real exit code, all failing assertions, and a raw-log path.

**Acceptance Scenarios**:

1. **Given** `/verify` runs `uv run pytest`, **When** compressed, **Then** the reported exit code and failure details match the raw run.
2. **Given** the user needs full output, **When** they ask, **Then** the raw log path (or `--raw` flag) is available.

---

### User Story 4 - Savings analytics and custom filters (Priority: P3)

`buddhi scripts rtk gain` reports tokens saved per command and in total (from a local JSON-lines log). Users can add project filters in `.buddhi/rtk/filters/*.json`, and `buddhi scripts rtk filters list|test|verify` manages them. Project-local filters require explicit trust before executing.

**Why this priority**: Observability and extensibility are valuable but not required for savings.

**Independent Test**: Run several commands, run `gain`, and check totals. Add a custom filter and verify it with inline tests.

**Acceptance Scenarios**:

1. **Given** past runs, **When** `gain` runs, **Then** it shows raw vs. filtered token estimates and a percentage per command.
2. **Given** an untrusted project filter, **When** a command matches, **Then** it is ignored with a notice until `trust` is granted.

---

### Edge Cases

- Binary or non-UTF-8 output: decode with `errors="replace"`, never crash.
- Interactive or streaming commands (TTY needed, `--watch`, `tail -f`): not rewritten.
- Very large output: bounded memory via streaming line processing and a hard cap.
- Windows (primary dev OS here): no POSIX-only assumptions. Handle `.cmd` shims, quoting, and CRLF.
- Commands carrying secrets in args: tracking log stores the command name only, with args redacted.
- Filter pitfalls: a filter that removes everything yields a "filtered to empty" notice plus raw tail instead of silence.
- Recursion: wrapped command must not be re-wrapped (env guard).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide `buddhi scripts rtk run -- <cmd...>` that executes the command, preserves exit code, and prints filtered output.
- **FR-002**: System MUST apply declarative JSON filters (strip/keep regex, replace, line dedup, head/tail limits, on-empty message, inline tests), format-compatible where practical with ported rtk filters.
- **FR-003**: System MUST port rtk's Apache-2.0 TOML filters (~60), converted to JSON, retaining upstream notices and marking them modified. No BUSL code or data is used.
- **FR-004**: System MUST provide a generic fallback filter for commands without a specific one.
- **FR-005**: System MUST never drop error/failure lines and MUST be fail-open on any filter error.
- **FR-006**: System MUST save raw output of failed commands to a recovery file and print its path.
- **FR-007**: System MUST provide `rtk rewrite <cmd>` returning the wrapped command or a no-rewrite signal, and an Antigravity `PreToolUse` hook (`.agents/hooks/`, registered in `hooks.json`) using it, fail-open and compatible with `guard_destructive.py`.
- **FR-008**: System MUST ship an always-on rule (`.agents/rules/`) and skill (`.agents/skills/`) per Antigravity formats, following the existing harness layout, and update `terminal-runner`, `verify`, `implement` guidance accordingly.
- **FR-009**: System MUST provide `rtk gain` (JSON-lines tracking, no network, no telemetry) and `rtk filters list|test|verify`.
- **FR-010**: Project-local filters MUST require explicit trust (hash-pinned) before use.
- **FR-011**: System MUST pass `ruff`, `mypy`, and `pytest` with new unit tests covering filters, rewrite, hook, exit-code preservation, and fail-open paths.
- **FR-012**: System MUST update `ACKNOWLEDGMENTS.md` (rtk-ai/rtk, Apache-2.0 text, BUSL exclusion note), `README.md`, and `CHANGELOG.md` under `[Unreleased]`.
- **FR-013**: Command arguments, tracking, and hook paths MUST work on Windows, macOS, and Linux.
- **FR-014**: Hook installation target format MUST follow Antigravity docs for rules/skills/subagents/hooks [NEEDS CLARIFICATION: docs at antigravity.google/docs were not fetched in this phase; confirm in `/spec-plan` research]. No UI surface, so the A11Y requirement does not apply.

### Key Entities

- **Filter**: TOML definition (match command regex, strip/keep/replace rules, limits, tests).
- **Rewrite Decision**: allow-unchanged, rewrite, or skip, plus reason.
- **Run Record**: timestamp, command name (args redacted), raw/filtered token estimates, exit code, raw-log path.
- **Trust Entry**: hash of a project-local filter file approved by the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On fixture outputs for common commands (git, pytest, ruff, mypy, uv, npm, cargo, docker), median token reduction is ≥ 60% (rtk's stated 60–90%).
- **SC-002**: 100% of fixture failure/error lines are preserved after filtering.
- **SC-003**: Exit code equals the raw command's in 100% of tests.
- **SC-004**: Hook adds under 200 ms overhead per command and never blocks a command on internal error.
- **SC-005**: Full `uv run pytest`, `ruff check`, `ruff format --check`, and `mypy src/ tests/` pass.
- **SC-006**: Provenance: every ported filter file carries upstream attribution, and no file under rtk `engine/` or `proxy/` is referenced.

## Assumptions

- Targets are Antigravity (agent and IDE) users running buddhi-cli on Python ≥ 3.10.
- Token counts are estimated (chars/4 heuristic) with no tokenizer dependency.
- Only Antigravity hook integration is in scope. rtk's other agent installers are excluded.
- rtk's Rust engine features beyond Apache-scope filters (compression engine, retriever, remote pipelines, telemetry) are out of scope.
- No new dependency: stdlib only. Filters are JSON (converted from rtk TOML) so `tomli` is not needed on Python 3.10.
- Existing patterns reused: `src/buddhi/scripts/` subcommand groups, `.agents/hooks/` fail-open hooks, autoharness's atomic-write and locking helpers.
