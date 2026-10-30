# Feature Specification: `/agents-md` skill (create & update AGENTS.md)

**Feature Branch**: `012-agents-skill`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Develop a skill to create and update `AGENTS.md` based on the repository it is in, optimized for Google Antigravity and the existing SDD workflow. Keep the top-line file concise (~12 lines). Update Changelog [Unreleased], `ACKNOWLEDGEMENT.md`, and README."

## Decisions (from clarification)

- New skill `/agents-md`; `audit-agents` stays as the separate principles audit (manual-only). `/agents-md` may hand off to it but does not replace or extend it.
- Skill ships in `.agents/skills/agents-md/` **and** in the generator templates so generated harnesses get it. A `buddhi skills` install flag is added only if the existing `--repo-to-skill` pattern calls for it (decide in `/spec-plan`).
- Update mode preserves user-written content: section-level merge, diff shown, no overwrite without confirmation. The ~12-line budget applies to the core block; detail is deferred to linked SKILL.md files and docs.
- Note: `.buddhi/specs/011-agents-skill-create/` is an untouched template from an earlier attempt at this feature; superseded by this spec and safe to delete.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate AGENTS.md for a repo without one (Priority: P1)

A maintainer runs `/agents-md` in a repo with no `AGENTS.md`. The skill inspects manifests, lockfiles, CI config and the code graph/OKF docs, then writes a concise `AGENTS.md` with: one-line overview, verified install/build/test/lint/typecheck commands, key components, and pointers to relevant `SKILL.md`/rules/docs.

**Why this priority**: Core value. Alone it delivers the benchmark benefit (fewer wrong-command loops).

**Independent Test**: Run on a sample Python repo (pyproject + pytest + ruff) and a Node repo; check output commands match the manifests and the core block is ≤ ~12 lines.

**Acceptance Scenarios**:

1. **Given** a repo with no `AGENTS.md`, **When** `/agents-md` runs, **Then** an `AGENTS.md` is created whose core block is ≤ ~12 lines.
2. **Given** `pyproject.toml` with uv, pytest, ruff and mypy, **When** the skill runs, **Then** the listed commands match those tools and each command is derived from repo evidence, not guessed.
3. **Given** detected skills under `.agents/skills/`, **When** the file is written, **Then** it points to them by path instead of inlining their content.

---

### User Story 2 - Update an existing AGENTS.md safely (Priority: P2)

A maintainer runs `/agents-md` after tooling changed. The skill compares the file with repo evidence, proposes edits as a diff, and preserves hand-written sections.

**Why this priority**: Files rot; the bulk of real use is updating. Depends on P1 detection logic.

**Independent Test**: Change the test runner in the manifest, run on a file with a custom section; verify the command is fixed and the custom section is byte-identical.

**Acceptance Scenarios**:

1. **Given** an `AGENTS.md` with a stale command, **When** the skill runs, **Then** it proposes a diff correcting it and applies it only after confirmation.
2. **Given** user-authored sections unrelated to detected facts, **When** updating, **Then** they are left unchanged.
3. **Given** a core block already over budget, **When** updating, **Then** the skill proposes moving detail to linked docs rather than silently truncating.

---

### User Story 3 - Fit Antigravity and SDD workflow (Priority: P3)

The skill follows Antigravity skill/rule conventions (valid `SKILL.md` frontmatter, concise description for triggering, progressive disclosure via `references/`), grounds itself with `buddhi_search`/OKF docs, verifies commands via `terminal-runner`, and is referenced from the SDD flow (e.g. `/spec-plan` AGENTS.md compliance check, harness rules).

**Why this priority**: Integration polish; skill is usable without it.

**Independent Test**: Skill validates against repo skill conventions; `buddhi skills` inventory lists it; a generated harness contains it.

**Acceptance Scenarios**:

1. **Given** a fresh `buddhi init` output, **When** inspected, **Then** `agents-md` skill is present with valid frontmatter.
2. **Given** a detected command, **When** the skill is unsure it works, **Then** it runs it via `terminal-runner` and reports real exit code, or marks it unverified.

---

### Edge Cases

- Monorepo with multiple packages: root file stays short; per-package `AGENTS.md` proposed, not inlined.
- No manifest or conflicting tools (e.g. both npm and pnpm lockfiles): ask the user, do not guess.
- `CLAUDE.md`/`GEMINI.md` already present: report overlap; do not duplicate content.
- Non-writable or git-dirty `AGENTS.md`: show diff and stop for confirmation.
- Existing file contains secrets or stale paths: flag, never copy them forward.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide `.agents/skills/agents-md/SKILL.md` with valid frontmatter (`name`, `description`) invocable as `/agents-md`.
- **FR-002**: Detect repo facts from manifests, lockfiles, CI config, README, existing agent rule files, the code graph, and `.buddhi/docs/`.
- **FR-003**: Generate `AGENTS.md` with a core block of ~12 lines (overview, commands, key components, pointers).
- **FR-004**: Every listed command must trace to repo evidence; unverifiable ones are marked or omitted.
- **FR-005**: Update mode merges by section, preserves user-authored content, shows a diff, and requires confirmation before writing.
- **FR-006**: Defer granular guidance to `SKILL.md`, rules, and docs via links rather than inlining.
- **FR-007**: Ship the skill in generator templates (`src/buddhi/templates/agents/skills/agents-md/`) so generated harnesses include it by default, and register it in `buddhi skills` with `--agents-md` flag for on-demand installation into existing harnesses.
- **FR-008**: Integrate with SDD: reference it where `/spec-plan` checks AGENTS.md compliance and from harness rules, without making it mandatory.
- **FR-009**: Add a CHANGELOG entry under `[Unreleased]`, references in `ACKNOWLEDGEMENT.md` (AAIF benchmark study, Antigravity skills and rules docs), and a README update.
- **FR-010**: Ground the design in the Antigravity skills (`antigravity.google/docs/skills/`) and rules (`antigravity.google/docs/rules/`) docs; record findings in `plan.md`.
- **FR-011**: Skill text follows antislop-code/copywriting guidance (no filler).
- **FR-012**: No UI surface, so no A11Y requirement applies.

### Key Entities

- **Repo facts**: detected commands, components, skills, with evidence source.
- **AGENTS.md core block**: the ≤ ~12-line top section; **extended sections**: user/detail content kept outside the budget.

## Success Criteria *(mandatory)*

- **SC-001**: Generated core block ≤ 12–15 lines on all test repos.
- **SC-002**: 100% of listed commands trace to repo evidence in a fixture test.
- **SC-003**: Updating a file with custom sections leaves those sections unchanged (byte-identical) in tests.
- **SC-004**: `uv run pytest`, `ruff check`, and `mypy` pass; the skill appears in `buddhi skills` and in generated harness output.
- **SC-005**: CHANGELOG, ACKNOWLEDGEMENT.md, and README updated and consistent.

## Assumptions

- AAIF benchmark figures (26% diff, 27% time, 25% tokens) are cited as context, not re-verified here.
- Python 3.10+ and the existing skill-bundling mechanism are reused.
