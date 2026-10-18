# Feature Specification: Integrate A11Y.md into Antigravity Harness and Spec-Driven Workflow

**Feature Branch**: `006-integrate-a11y-into`

**Created**: 2026-10-27

**Status**: Approved

**Input**: User description: "Analyze the `A11Y.md` project located in `./temp/A11Y.md/` and understand how it is implemented for AI coding assistants. Then plan how it can be integrated for Antigravity harness in `buddhi-cli` making it highly customized to work with Antigravity as well as the existing Spec Driven Workflow that initialize with `buddhi init`. Once implementation is completed, update the `ACKNOWLEDGEMENT.md` with reference to the original repo (`https://github.com/fecarrico/A11Y.md`). Update changelog with this new implementation under `[unreleased]`. Finally update the `README.md` accordingly (if needed only)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Normative A11Y Skill, Reference Library & Always-On Rule in Antigravity Harness (Priority: P1)

When a developer runs `buddhi init` on a project, `buddhi-cli` scaffolds the adapted `A11Y.md` (v2.5.0) persistent accessibility context system directly into `.agents/`: an always-on constraint rule (`.agents/rules/a11y.md`), the core `a11y` skill (`.agents/skills/a11y/SKILL.md`), all 31 WAI-ARIA APG and platform reference guides (`.agents/skills/a11y/references/guide-*.md`), and all 4 lifecycle governance templates (`.agents/skills/a11y/templates/*.md`). The core skill is customized for Google Antigravity, replacing generic external URL/script instructions with `buddhi scripts verify-a11y`, `buddhi scripts contrast`, Buddhi MCP tools (`buddhi_search`, `buddhi_read`, `buddhi_memory`, `check_contrast`, `verify_a11y`), and Antigravity's `invoke_subagent` for fresh-context independent verification.

**Why this priority**: This is the foundational persistent context layer required for every AI coding session, specialist subagent, and SDD phase to enforce WCAG 2.2 / ADA / EAA / ABNT NBR 17225 accessibility constraints from the first line of UI code.

**Independent Test**: Run `uv run pytest` testing `buddhi init` in a temporary directory and verify that `.agents/rules/a11y.md`, `.agents/skills/a11y/SKILL.md`, all 31 reference guides under `.agents/skills/a11y/references/`, and all 4 governance templates under `.agents/skills/a11y/templates/` are scaffolded idempotently without overwriting existing user files.

**Acceptance Scenarios**:

1. **Given** an uninitialized or existing repository, **When** the user runs `buddhi init`, **Then** `.agents/rules/a11y.md` and `.agents/skills/a11y/` (containing `SKILL.md`, 31 `references/guide-*.md` files, and 4 `templates/*.md` files) are created idempotently.
2. **Given** an AI agent working on UI, frontend, or mobile tasks in Antigravity, **When** `.agents/rules/a11y.md` triggers, **Then** the agent loads `.agents/skills/a11y/SKILL.md`, resolves the Compliance Profile (`Standard (AA)` default, `Shield (AAA)`, or `Launchpad (A)`), and lazy-loads only the matching §2.1 component reference guides from `.agents/skills/a11y/references/`.
3. **Given** `antislop-human` and `a11y` both present in `.agents/skills/`, **When** an agent performs UI work, **Then** `antislop-human` acts as the visual anti-slop filter while `a11y` governs normative WCAG 2.2 compliance, APG semantics, and governance artifacts without conflicting instructions.

---

### User Story 2 - Deterministic A11Y Static Gate & Enhanced Contrast CLI / MCP Tooling (Priority: P2)

Developers and Antigravity agents can execute `A11Y.md`'s deterministic verification and contrast tools natively through `buddhi scripts` and `buddhi-mcp`:
1. `buddhi scripts verify-a11y`: Runs the `A11Y.md` static gate (`src/buddhi/scripts/verify_a11y.py`), validating governance artifacts (`REPORT.md`, `EXCEPTIONS.md`, `A11Y-DECISIONS.md`), report freshness against git/mtime, compliance status and verification independence ceilings (`cross-agent`, `fresh-context`, `self-reported`), recomputed contrast evidence tables, §2.1 component guide coverage against source markup/scripts, exception sign-offs/expiries, registered decision/exception suppressions, and 11 source anti-patterns (`clickable-div`, `placeholder-label`, `half-climbed-aria`, `aria-soup`, `nullified-alt`, `orphaned-aria`, `overlay`, `positive-tabindex`, `outline-none`, `redundant-alert`, `media-autoplay`).
2. `buddhi scripts contrast`: Preserves 100% backward compatibility with `buddhi scripts contrast <color_a> <color_b>` and `--selftest`, while adding `A11Y.md` multi-pair mode (`--bg` / `--fg` / `--profile [standard|shield]` with ready-to-paste `REPORT.md` table rows) and CSS triage mode (`--css` / `--page-bg` with RGBA/HSLA alpha compositing).
3. `buddhi-mcp` server tools: Exposes `verify_a11y` and enhanced `check_contrast` on the MCP server so agents can run static gate and contrast checks directly.

**Why this priority**: The `A11Y.md` Behavioral Contract (§2 *Static Gate* and §3 *Perceivable — Contrast*) mandates running deterministic verification and contrast computation rather than estimating ratios or trusting unverified claims.

**Independent Test**: Run `buddhi scripts verify-a11y --selftest` and `buddhi scripts contrast --selftest` (plus unit tests for pair mode, CSS triage mode, artifact location resolution, and MCP tool invocation) and verify exit code `0` with all fixture cases passing.

**Acceptance Scenarios**:

1. **Given** the `buddhi` CLI, **When** `buddhi scripts verify-a11y --selftest` is executed, **Then** all built-in fixture cases (clean project, clickable divs, placeholder labels, half-climbed ARIA, ARIA soup, nullified alt, overlay scripts, contrast evidence math, guide coverage, and exception/decision registers) pass with exit code `0`.
2. **Given** a project with UI source files and `REPORT.md` (at root, `.buddhi/a11y/REPORT.md`, or `.buddhi/specs/<branch>/REPORT.md`), **When** `buddhi scripts verify-a11y [PROJECT_DIR] [--src SUBDIR] [--warn-only]` runs, **Then** it checks artifacts and source anti-patterns and outputs the exact `Static gate` summary line for `REPORT.md`.
3. **Given** `buddhi scripts contrast`, **When** called with `<color_a> <color_b>`, **Then** it outputs the existing format and exit code; **When** called with `--bg <color> --fg <color>... [--profile standard|shield]` or `--css <file> [--page-bg <color>]`, **Then** it computes alpha-composited WCAG ratios, prints `REPORT.md` markdown table rows in pair mode, or flags failing CSS pairs in triage mode.
4. **Given** the `buddhi-mcp` server, **When** an agent invokes `verify_a11y` or `check_contrast`, **Then** the server returns structured static gate findings or contrast calculations.

---

### User Story 3 - Spec-Driven Development (SDD) Lifecycle & Subagent Integration (Priority: P3)

The SDD lifecycle skills (`/specify`, `/spec-plan`, `/spec-tasks`, `/implement`, `/verify`, `/close-spec`) and the `frontend-specialist` subagent work cohesively with the `a11y` skill and governance artifacts:
- `/specify`: Prompts for the target A11Y Compliance Profile (`Standard (AA)` default, `Shield (AAA)`, `Launchpad (A)`) on UI-touching features and embeds accessibility acceptance criteria in `spec.md`.
- `/spec-plan` & `frontend-specialist`: Grounds UI plans in existing components via `buddhi_search` (*Component Reuse*), consults `A11Y-DECISIONS.md` and OKF memory (*Decision Memory*), and maps planned UI components to their §2.1 reference guides (`guide-*.md`).
- `/spec-tasks` & `/implement`: Enforces lazy loading of §2.1 reference guides per component slice, developer-in-the-loop Image/Media Evidence resolution, recording pattern choices in `A11Y-DECISIONS.md`, and logging any accepted SC deviation in `EXCEPTIONS.md`.
- `/verify`: Runs `buddhi scripts verify-a11y` via `terminal-runner`, updates `REPORT.md`, and dispatches an unprimed fresh-context subagent (`invoke_subagent`) to independently reproduce the automated Section 7 checkpoints so `REPORT.md` achieves `fresh-context` verification independence.
- `/close-spec` & `sdd-promote`: Promotes durable accessibility pattern decisions from `A11Y-DECISIONS.md` into OKF memory (`.agents/memory/decisions/`) and prompts to draft/update root `ACCESSIBILITY.md` when shipping a public release.

**Why this priority**: Connects `A11Y.md` from a standalone instruction file into an automated, end-to-end engineering workflow across specification, architecture planning, task slicing, implementation, independent verification, and memory archival.

**Independent Test**: Inspect scaffolded SDD skills, `frontend-specialist.md`, and `sdd-promote` unit tests to verify that A11Y compliance profiles, §2.1 guide mapping, static gate execution, fresh-context subagent verification, and `A11Y-DECISIONS.md` memory promotion work end-to-end.

**Acceptance Scenarios**:

1. **Given** a UI feature in SDD, **When** `/specify` and `/spec-plan` run, **Then** the compliance profile and required §2.1 component guides are documented in `spec.md` and `plan.md`, and `frontend-specialist` checks component reuse via `buddhi_search` and `A11Y-DECISIONS.md`.
2. **Given** a completed UI implementation, **When** `/verify` runs, **Then** it executes `buddhi scripts verify-a11y` via `terminal-runner` and spawns a fresh-context subagent to audit Section 7 automated checkpoints and record `fresh-context` independence in `REPORT.md`.
3. **Given** a shipped spec with `A11Y-DECISIONS.md`, **When** `buddhi memory sdd-promote` (or `/close-spec`) runs, **Then** pattern decisions from `A11Y-DECISIONS.md` are promoted into OKF decision concept nodes under `.agents/memory/decisions/`.

---

### User Story 4 - Project Attribution, Changelog & Documentation Updates (Priority: P4)

Update `ACKNOWLEDGMENTS.md` with full attribution and MIT license text for `fecarrico/A11Y.md` (`https://github.com/fecarrico/A11Y.md`), document the integration under `[Unreleased]` in `CHANGELOG.md`, and update `README.md` (and synced `.agents/` files in the repository) to reflect the new `a11y` skill, rule, CLI scripts, and MCP tool.

**Why this priority**: Fulfills explicit user requirements and open-source MIT license obligations while keeping project documentation accurate.

**Independent Test**: Verify `ACKNOWLEDGMENTS.md` contains `https://github.com/fecarrico/A11Y.md` and its MIT license, `CHANGELOG.md` documents the new features under `[Unreleased]`, and `README.md` accurately lists the new capabilities.

**Acceptance Scenarios**:

1. **Given** `ACKNOWLEDGMENTS.md`, **When** inspected after implementation, **Then** it includes a dedicated section for `A11Y.md` (`https://github.com/fecarrico/A11Y.md`, Author: Felipe A. Carriço / `fecarrico`, MIT License) detailing the adapted skills, rules, reference guides, templates, and CLI/MCP tools.
2. **Given** `CHANGELOG.md` and `README.md`, **When** inspected after implementation, **Then** `CHANGELOG.md` lists the `A11Y.md` integration under `## [Unreleased]` and `README.md` reflects the updated skill, script, and MCP capabilities.

---

### Edge Cases

- **Backward Compatibility of `buddhi scripts contrast`**: Existing callers and tests invoke `buddhi scripts contrast "#FFFFFF" "#777777"` with two positional arguments and expect `ratio: ... / normal text (4.5:1): ... / large text (3.0:1): ...`. New flags (`--bg`, `--fg`, `--css`, `--page-bg`, `--profile`, `--selftest`) MUST NOT break existing positional invocation or existing unit tests.
- **Artifact Path Resolution in `verify-a11y`**: Projects may store `REPORT.md`, `EXCEPTIONS.md`, and `A11Y-DECISIONS.md` at the repository root (upstream `A11Y.md` convention), under `.buddhi/a11y/`, or inside an active SDD spec folder (`.buddhi/specs/<branch>/`). `verify_a11y.py` MUST support resolving artifacts from root first, with fallback to `.buddhi/a11y/` or explicit `--report-dir` / `--src` options, while keeping upstream's 31 self-test cases passing 100%.
- **Non-UI / Backend-Only Features in SDD**: SDD skills (`/specify`, `/spec-plan`, `/implement`, `/verify`, `/close-spec`) MUST treat A11Y gates as conditional on UI/frontend/mobile scope so backend-only or CLI-only features are not blocked by missing `REPORT.md` files.
- **File Size Ratchet (`check-file-size`)**: Every new Python module under `src/buddhi/` and test file under `tests/` MUST stay well below the 8,000-token (32 KB) ceiling enforced by `buddhi scripts check-file-size --all` (splitting `verify_a11y` into modular submodules if needed).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `buddhi init` MUST scaffold `.agents/rules/a11y.md` as an always-on constraint rule for UI/frontend/mobile work.
- **FR-002**: `buddhi init` MUST scaffold `.agents/skills/a11y/SKILL.md` (adapted from `A11Y.md` v2.5.0 for Antigravity and `buddhi-cli`), `.agents/skills/a11y/references/guide-*.md` (all 31 reference guides), and `.agents/skills/a11y/templates/*.md` (`REPORT.md`, `EXCEPTIONS.md`, `A11Y-DECISIONS.md`, `ACCESSIBILITY.md`).
- **FR-003**: `buddhi scripts verify-a11y` MUST provide the full static gate from `A11Y.md`'s `verify-a11y.py` (artifact checks, freshness, status, independence, standard-version, gate-declared, contrast-evidence arithmetic recomputation, 17-signature component guide coverage, exception sign-off/expiry validation, register suppressions, and 11 source anti-pattern checks) plus `--selftest` (and `--self-test` alias).
- **FR-004**: `buddhi scripts contrast` MUST preserve its existing two-color positional CLI (`buddhi scripts contrast <color_a> <color_b>` and `--selftest`) while adding `--bg`, `--fg`, `--profile [standard|shield]`, `--css`, and `--page-bg` modes from `A11Y.md`'s `contrast-check.py` (supporting hex, named `black`/`white`, `rgb`/`rgba`, and `hsl`/`hsla` with alpha compositing).
- **FR-005**: `buddhi-mcp` (`src/buddhi/mcp/server.py`) MUST expose a `verify_a11y` tool and support profile/alpha-aware contrast verification so agents can execute static gate and contrast checks via MCP.
- **FR-006**: SDD skills (`specify`, `spec-plan`, `spec-tasks`, `implement`, `verify`, `close-spec`), `quick-plan`, `frontend-specialist`, and `AGENTS.md` template MUST be updated to integrate `A11Y.md` compliance profiles, §2.1 lazy reference loading, `A11Y-DECISIONS.md` / `EXCEPTIONS.md` / `REPORT.md` lifecycle management, `buddhi scripts verify-a11y`, and fresh-context subagent verification.
- **FR-007**: `buddhi memory sdd-promote` (`src/buddhi/memory/sdd_bridge.py`) MUST extract pattern decisions from `A11Y-DECISIONS.md` (when present in the project or spec directory) into durable OKF decision concepts under `.agents/memory/decisions/`.
- **FR-008**: `ACKNOWLEDGMENTS.md`, `CHANGELOG.md` (under `[Unreleased]`), and `README.md` MUST be updated with full attribution to `https://github.com/fecarrico/A11Y.md` and documentation of the new capabilities.

### Key Entities

- **A11Y Skill & Reference Bundle (`.agents/skills/a11y/`)**: Normative core (`SKILL.md`), 31 component/platform reference guides (`references/guide-*.md`), and 4 governance templates (`templates/*.md`).
- **Governance Artifacts (`REPORT.md`, `EXCEPTIONS.md`, `A11Y-DECISIONS.md`, `ACCESSIBILITY.md`)**: Versioned project records tracking verification evidence, accepted WCAG deviations with expiry/owners, pattern-indexed conformant choices, and the public accessibility statement.
- **Static Gate Result (`VerifyA11yResult`)**: Structured output of `verify_a11y` containing `errors`, `warnings`, `registered` findings, pass/fail verdict, and the formatted `REPORT.md` static gate record line.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `buddhi init` scaffolds `.agents/rules/a11y.md`, `.agents/skills/a11y/SKILL.md`, all 31 reference guides, and all 4 templates with 100% idempotency on re-runs.
- **SC-002**: `buddhi scripts verify-a11y --selftest` passes all 31 upstream fixture test cases with exit code `0`, and `buddhi scripts contrast --selftest` passes both the `antislop-human` reference table and `A11Y.md` alpha/HSL/RGB boundary fixture cases with exit code `0`.
- **SC-003**: All existing and new `pytest` suites, `ruff check`, `ruff format --check`, `mypy src/ tests/`, and `buddhi scripts check-file-size --all` pass with zero errors.
- **SC-004**: `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md` are updated and verified.

## Assumptions

- English (`docs/en/`) is the canonical language for the scaffolded Antigravity harness skills, rules, reference guides, and templates (matching all other skills in `buddhi-cli`).
- The temporary `./temp/A11Y.md/` directory is a reference checkout for analysis and is not packaged into the wheel; all integrated templates and code live under `src/buddhi/` and `.agents/`.
