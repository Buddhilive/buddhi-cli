# Feature Specification: Polished CLI Output, 1.0.0 Release

**Feature Branch**: `014-polished-cli-output`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "Update the output and presentation of commands like `buddhi init` to be well presented and attractive, with an ASCII-art "BuddhiAI CLI" title and the tool version. Bump the version to `1.0.0`, move the CHANGELOG `[Unreleased]` entries under that version, and verify the full tool works."

## Grounding

- `src/buddhi/commands/init.py` prints plain `console.print` lines (rich `Console`); no banner.
- Other commands using rich: `generate.py`, `graph_cmd.py`, `docs.py`, `memory.py`, `scripts.py`, `skills.py`.
- Version is only in `pyproject.toml` (`1.0.0b11`); no `--version` flag and no `__version__` in `src/buddhi/`.
- `CHANGELOG.md` has `## [Unreleased]` above `## [1.0.0-beta.11] - 2026-09-13`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Branded `buddhi init` output (Priority: P1)

A user runs `buddhi init`. They see an ASCII-art "BuddhiAI CLI" title with the version, then a clearly structured summary (graph stats, docs plan, `.agents/` scaffolding, written files, next step) instead of plain lines.

**Why this priority**: `init` is the first-run experience and the user's primary ask.

**Independent Test**: Run `buddhi init` in a temp dir; the banner, version and summary sections appear and exit code is 0.

**Acceptance Scenarios**:

1. **Given** a project directory, **When** `buddhi init` runs, **Then** the banner shows "BuddhiAI CLI" and the current version before any other output.
2. **Given** init completes, **When** the summary prints, **Then** it groups graph, docs plan, `.agents/`, written files, and next step with consistent styling.
3. **Given** stdout is not a TTY (piped, `NO_COLOR`, or narrow terminal), **When** init runs, **Then** output stays readable: no escape codes when color is off, and the banner falls back to a one-line title if width is too small.
4. **Given** errors (bad path), **When** init fails, **Then** the error goes to stderr with exit code 1, unchanged in meaning.

---

### User Story 2 - `--version` and consistent styling across commands (Priority: P2)

`buddhi --version` prints the banner with the version. Other commands (`generate`, `graph`, `docs`, `memory`, `skills`, `scripts`) share the same styling helpers (status icons, panels, tables) but do not print the big banner.

**Why this priority**: Consistency, but `init` works as an MVP without it.

**Independent Test**: `buddhi --version` exits 0 and shows banner + version; `buddhi generate` output uses shared styling without the banner.

**Acceptance Scenarios**:

1. **Given** the installed tool, **When** `buddhi --version`, **Then** banner and version matching `pyproject.toml` are shown.
2. **Given** a command that emits machine-readable output (`--json`, MCP stdio), **When** run, **Then** output is unchanged and unstyled.

---

### User Story 3 - 1.0.0 release metadata (Priority: P2)

Maintainers see version `1.0.0` in `pyproject.toml` and the CLI, and CHANGELOG `[Unreleased]` content filed under `## [1.0.0] - 2026-10-30` with a fresh empty `[Unreleased]` above.

**Why this priority**: Required for release, independent of visuals.

**Independent Test**: Version string equals `1.0.0` everywhere; CHANGELOG headings are correct.

**Acceptance Scenarios**:

1. **Given** the repo, **When** version is read from package metadata, **Then** it is `1.0.0`.
2. **Given** CHANGELOG, **When** viewed, **Then** a new empty `[Unreleased]` precedes `[1.0.0] - 2026-10-30`, containing the former unreleased entries, including this feature.

---

### User Story 4 - Full-tool verification (Priority: P1)

The full tool is verified: tests, lint, format, typecheck, build, and a real smoke run of core commands.

**Why this priority**: The user explicitly requires proof the tool works.

**Independent Test**: `uv run pytest`, `ruff check`, `ruff format --check`, `mypy src/ tests/`, `uv build` all exit 0; smoke run of `init`, `generate`, `--version` in a temp dir succeeds.

**Acceptance Scenarios**:

1. **Given** the finished change, **When** the verify commands run, **Then** all exit 0 with evidence recorded.
2. **Given** a built wheel, **When** installed and `buddhi --version` run, **Then** it reports `1.0.0`.

### Edge Cases

- Windows legacy consoles with non-UTF-8 encoding: banner must not crash (ASCII-only art or safe fallback).
- Very narrow terminals (<60 columns).
- `NO_COLOR` / non-TTY / CI logs.
- Existing tests asserting on exact `init` output strings may need updating.
- Version lookup when running from an uninstalled source tree.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `buddhi init` MUST print an ASCII-art "BuddhiAI CLI" banner with the tool version before other output.
- **FR-002**: `init` summary MUST be organized into styled sections (graph, docs plan, `.agents/`, files written, next step) preserving all current information.
- **FR-003**: `buddhi --version` MUST print the banner and version.
- **FR-004**: Shared output helpers MUST be used by the other rich-based commands for consistent status styling; the big banner MUST NOT appear in them.
- **FR-005**: Output MUST degrade gracefully for non-TTY, `NO_COLOR`, narrow width, and non-UTF-8 consoles.
- **FR-006**: JSON and machine-readable outputs MUST remain unchanged.
- **FR-007**: Version MUST be `1.0.0` in `pyproject.toml`, with a single source of truth the CLI reads at runtime.
- **FR-008**: CHANGELOG `[Unreleased]` entries MUST move under `## [1.0.0] - 2026-10-30` with a new empty `[Unreleased]` section, and the link/format conventions preserved.
- **FR-009**: Tests MUST cover the banner, version display, and fallback behavior; existing tests MUST be updated only where output formatting legitimately changed.
- **FR-010**: Full verification (pytest, ruff, mypy, build, smoke runs) MUST pass with recorded evidence.

### Key Entities

- **Banner**: ASCII title plus version, rendered with width-aware fallback.
- **Output helpers**: Shared styling functions (status line, section panel, key/value table).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `buddhi init` and `buddhi --version` show the title and `1.0.0` in 100% of runs on a TTY.
- **SC-002**: Piped or `NO_COLOR` output contains zero ANSI escape sequences.
- **SC-003**: All verification commands exit 0; no existing test regresses.
- **SC-004**: No information currently printed by `init` is lost.
- **SC-005**: Banner never raises on a cp1252 / narrow console.

## Assumptions

- Banner only on `init` and `--version` (confirmed by user); other commands get shared styling only.
- Release date is today, 2026-10-30; CHANGELOG heading uses `[1.0.0]`.
- Rich is already a dependency, so no new dependencies are needed.
- Banner art is hand-authored ASCII (no figlet dependency).
- Version single source: `importlib.metadata` reading the installed package, with a fallback for source trees.
