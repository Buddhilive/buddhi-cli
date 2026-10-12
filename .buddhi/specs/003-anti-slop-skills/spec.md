# Feature Specification: Anti-Slop Skills, Rules & Scripts Integration

**Feature Branch**: `003-anti-slop-skills`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Analyze the `anti-slop` project in `./temp/anti-slop/`, verify its license, and (if permitted) adapt its skills/rules to Antigravity harness style in `buddhi init`, port its scripts to Python as `buddhi scripts ...` commands, add `ACKNOWLEDGMENTS.md`, and update `README.md` and `CHANGELOG.md` (under [Unreleased])."

## Licensing Finding

Upstream (`miqdadbadjuber/anti-slop`) is **MIT-licensed** (`temp/anti-slop/LICENSE`, "Copyright (c) 2026 Miqdad Badjuber (antislop)"). Adapting, modifying and redistributing is permitted provided the copyright and permission notice are retained. Therefore: adaptation is allowed; `ACKNOWLEDGMENTS.md` must include the upstream copyright and full MIT text.

## Upstream Analysis

| Upstream asset | Purpose | Buddhi disposition |
|---|---|---|
| `skills/antislop` | Core always-on filter, "Two Usage Modes" | Adapt as skill |
| `skills/antislop-ui`, `-copywriting`, `-human`, `-layoutmobile`, `-code` | Domain filters (UI, copy, people, mobile, code comments) | Adapt as skills |
| `rules/antislop.md` / `.mdc` | Always-on bootstrap rule pointing at skills | Adapt as Antigravity rule (`.agents/rules/antislop.md`); drop Cursor `.mdc` |
| `skills/antislop-human/contrast-check.py` | WCAG 2.x contrast checker (+ `--selftest`) | Port into `buddhi scripts contrast` |
| `skills/antislop-human/contrast-mcp.py` | MCP stdio server exposing contrast tool | Not ported; replaced by a `check_contrast` tool in the existing `buddhi mcp` server |
| `scripts/check-repo.mjs`, `skill-index.mjs`, `cli/*`, `.*-plugin/*` | Upstream repo CI, multi-tool installer, plugin manifests | **Out of scope** (upstream-specific tooling for other agents) |

> [!NOTE]
> Partial, uncommitted drafts of the six skills already exist under `src/buddhi/templates/agents/skills/antislop*` and `frontend-specialist.md` has been edited. Per user decision they are the **baseline**: audit and complete them rather than start over.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anti-slop skills & rule ship with `buddhi init` (Priority: P1)

A developer runs `buddhi init` and gets the anti-slop skill set and always-on rule installed in their Antigravity workspace, so their agent filters generic AI-generated UI, copy and code.

**Why this priority**: Core value of the feature and a standalone MVP; no scripts needed.

**Independent Test**: Run `buddhi init` in an empty temp directory and inspect `.agents/`.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** `buddhi init` runs, **Then** `.agents/skills/antislop*/SKILL.md` (6 skills) and `.agents/rules/antislop.md` exist.
2. **Given** each installed skill, **When** its frontmatter is parsed, **Then** it has valid `name` (matching folder) and `description` per Antigravity skill format, and the rule follows Antigravity rule format.
3. **Given** an existing workspace with user-modified antislop files, **When** `buddhi init` re-runs, **Then** existing init overwrite/skip behavior is respected (no silent data loss).
4. **Given** `frontend-specialist` agent, **When** viewed, **Then** it references the `antislop-ui` / `antislop-layoutmobile` skills.

---

### User Story 2 - `buddhi scripts contrast` WCAG checker (Priority: P2)

A developer or agent runs `buddhi scripts contrast "#FFFFFF" "#777777"` and gets the ratio and PASS/FAIL for normal (4.5:1) and large (3:1) text; exit code 0 only if both pass.

**Why this priority**: Supports the `antislop-human`/UI skills with deterministic verification; depends on US1 only for documentation references.

**Independent Test**: Run the command with known pairs (black/white = 21:1) and `--selftest`.

**Acceptance Scenarios**:

1. **Given** `#FFFFFF` and `#000000`, **When** the command runs, **Then** it prints `21.00:1`, both verdicts PASS, exit code 0.
2. **Given** `FFFFFF 777777` (no `#`) or 3-digit hex / `black`/`white`, **When** run, **Then** they are parsed correctly.
3. **Given** an invalid color, **When** run, **Then** a clear error is printed and exit code is non-zero (not a traceback).
4. **Given** `--selftest`, **When** run, **Then** the reference table in the shipped `antislop-human/SKILL.md` is recomputed and any mismatch fails.

---

### User Story 3 - Attribution & documentation (Priority: P3)

Maintainers/users can see credit to upstream and discover the feature.

**Why this priority**: Required for MIT compliance and discoverability, but no runtime effect.

**Independent Test**: Review files.

**Acceptance Scenarios**:

1. **Given** the repo root, **When** listed, **Then** `ACKNOWLEDGMENTS.md` exists with link to `https://github.com/miqdadbadjuber/anti-slop`, the upstream copyright line and full MIT text.
2. **Given** `README.md`, **When** read, **Then** it documents the anti-slop skills/rule installed by `init` and `buddhi scripts` usage, and links to the acknowledgments.
3. **Given** `CHANGELOG.md`, **When** read, **Then** the feature is listed under `[Unreleased]` (Added).

---

### Edge Cases

- Contrast input with alpha channel (8-digit hex) or `rgb()` notation: unsupported → clear error (or documented).
- `--selftest` when the packaged SKILL.md is missing or its table format changes → explicit failure message.
- Package-data: templates and scripts must be included in built wheel (verify `pyproject` package-data).
- `buddhi scripts` with no subcommand → shows help, exit 0.
- Windows console encoding for output characters.
- Upstream skills referencing Claude/Cursor-specific paths or tools (e.g. `skills/` plugin dir, `.mdc`) must be rewritten to `.agents/skills/`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `buddhi init` MUST install the six `antislop*` skills into `.agents/skills/` using Antigravity SKILL.md format (frontmatter `name`, `description`).
- **FR-002**: `buddhi init` MUST install an always-on `antislop` rule into `.agents/rules/` following Antigravity rule conventions, adapted from upstream `rules/antislop.md` (paths rewritten, no Cursor `.mdc`).
- **FR-003**: Adapted content MUST preserve the upstream copyright attribution where substantial text is retained (e.g. a short "Adapted from antislop (MIT)" note) and MUST remove references to non-Antigravity tooling.
- **FR-004**: The CLI MUST expose a `buddhi scripts` command group with a `contrast` subcommand implemented in Python, with no new third-party dependencies.
- **FR-004b**: The CLI MUST also provide `buddhi scripts antislop-mode [during|after|ask]` (port of upstream `cli/lib/settings.mjs` mode setting) because the adapted core skill's "Two Usage Modes" depends on it. Shows the current mode when no argument is given; never overwrites an unparseable settings file.
- **FR-005**: `buddhi scripts contrast` MUST accept two colors (hex with/without `#`, 3 or 6 digits, `black`/`white`), print ratio and normal/large PASS/FAIL, and exit 0 only if both pass.
- **FR-006**: `buddhi scripts contrast --selftest` MUST validate the SKILL.md reference table against the WCAG formula.
- **FR-007**: The existing `buddhi mcp` server (`src/buddhi/mcp`) MUST be extended with a `check_contrast` tool reusing the same contrast logic as `buddhi scripts contrast`. The upstream standalone `contrast-mcp.py` server MUST NOT be ported.
- **FR-008**: Upstream repo tooling (`check-repo.mjs`, `skill-index.mjs`, `cli/`, other-agent plugin manifests) MUST NOT be ported.
- **FR-009**: Existing partial drafts MUST be audited against upstream and Antigravity docs, and gaps completed (including `frontend-specialist.md` change and `.agents/` dogfood copy in this repo if the project mirrors templates).
- **FR-010**: `ACKNOWLEDGMENTS.md` MUST be created at repo root crediting `https://github.com/miqdadbadjuber/anti-slop`, including the MIT copyright notice and license text.
- **FR-011**: `README.md` MUST document the feature and `buddhi scripts`; `CHANGELOG.md` MUST list it under `[Unreleased]`.
- **FR-012**: Unit tests MUST cover contrast math, color parsing, CLI exit codes, and presence of init-installed antislop assets.
- **FR-013**: OKF docs (`.buddhi/docs/`) SHOULD be refreshed via `/document-codebase` after implementation.

### Key Entities

- **Skill template**: Folder with `SKILL.md` (+ optional resources) under `src/buddhi/templates/agents/skills/`.
- **Rule template**: Markdown file under `src/buddhi/templates/agents/rules/`.
- **Script command**: Typer subcommand under `buddhi scripts`, implemented in `src/buddhi/scripts/`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh `buddhi init` produces 6 antislop skills and 1 rule, 100% with valid frontmatter.
- **SC-002**: `buddhi scripts contrast` gives correct ratios (±0.01) for all rows in the reference table and `--selftest` passes.
- **SC-003**: The full test suite, lint and typecheck pass with no regressions.
- **SC-004**: `ACKNOWLEDGMENTS.md`, README and CHANGELOG changes are present, and the MIT notice is included.

## Assumptions

- Upstream skill text is adapted (not copied verbatim wholesale) and attributed; MIT permits either.
- Antigravity conventions (skills in `.agents/skills/<name>/SKILL.md`, rules in `.agents/rules/*.md`) match what `buddhi init` already installs for existing skills/rules.
- Python port uses stdlib only; Python version matches the project's minimum.
- No upstream network access needed at runtime.

## Open Questions

Resolved: MCP contrast is a `check_contrast` tool in the existing `buddhi mcp` server (FR-007); the antislop rule is always installed by `buddhi init`, as upstream does (FR-002, no opt-out flag).

1. Docs verification: Antigravity docs URLs (skills/rules/subagents) should be re-checked during `/spec-plan`.
