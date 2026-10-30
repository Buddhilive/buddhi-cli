# Feature Specification: DESIGN.md Skill & Design System Codification (`/design-md`)

**Feature Branch**: `013-design-skill`

**Created**: 2026-10-30

**Status**: Approved

**Input**: User description: "Based on the provided context and the references, develop a skill to create and update `DESIGN.md` file. Skill should be optimized for Google Antigravity and existing Spec Driven Development workflow in `buddhi-cli` adhering to the best practices for Antigravity. This skill should be a part of `buddhi init` initialization skills."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Update `DESIGN.md` via `/design-md` Skill & Helper Script (Priority: P1)

A developer or AI coding agent working in a repository with UI/frontend surfaces wants to codify or update a root `DESIGN.md` file conforming to the open-source Google Labs / Google Stitch `DESIGN.md` specification (`https://stitch.withgoogle.com/docs/design-md/specification` and `https://github.com/google-labs-code/design.md`). The agent invokes `/design-md`, which runs `.agents/skills/design-md/scripts/detect_design_md.py` (backed by `src/buddhi/skills/design_md/`) to inspect repository stylesheets, Tailwind configs, CSS custom properties, and theme token files, extract deterministic design tokens into the machine-readable YAML frontmatter layer, synthesize or preserve vivid human-readable design rationale prose (the most important layer—e.g., *"A graduate-level computer science lecture handout in the tradition of an old established university"*), and validate foreground/background contrast pairs against WCAG 2.2 AA standards.

**Why this priority**: The core value of `DESIGN.md` is eliminating stateless visual drift across AI coding sessions by combining machine-readable YAML tokens with vivid prose rationale and non-destructive updates. Without the `/design-md` skill, detector, merger, and linter, no downstream SDD or `buddhi init` integration can function.

**Independent Test**: Run `python .agents/skills/design-md/scripts/detect_design_md.py --diff`, `--json`, `--lint`, and `--apply` against a repository with CSS custom properties or Tailwind tokens, verify that `DESIGN.md` is created with valid two-layer structure (YAML frontmatter + canonical Markdown sections), and verify that re-running `--apply` on a customized `DESIGN.md` preserves hand-written aesthetic prose and custom sections byte-for-byte while updating extracted token tables/frontmatter.

**Acceptance Scenarios**:

1. **Given** a project containing CSS variables (`--color-primary`, `--font-sans`, etc.) or `tailwind.config.*` / `package.json` UI dependencies and no `DESIGN.md`, **When** the agent runs `detect_design_md.py --apply` (with optional `--aesthetic` prose prompt or detected defaults), **Then** a valid `DESIGN.md` is created at the project root containing both machine-readable YAML frontmatter (`name`, `version`, `colors`, `typography`, `spacing`, `rounded`, `elevation`) and the 8 canonical Markdown prose sections (`Overview`, `Colors`, `Typography`, `Layout`, `Elevation & Depth`, `Shapes`, `Components`, `Do's and Don'ts`).
2. **Given** an existing `DESIGN.md` where a developer or agent has crafted custom aesthetic prose in `## Overview`, `## Do's and Don'ts`, or custom sections (e.g., `## Brand Voice`), **When** CSS/Tailwind tokens change in the codebase and `detect_design_md.py --apply` is executed, **Then** the YAML frontmatter tokens and managed token reference summaries update while all custom aesthetic prose and unmanaged sections are preserved byte-for-byte.
3. **Given** a `DESIGN.md` file with defined color tokens (`primary`, `secondary`, `surface`, `background`, `text`, etc.), **When** `detect_design_md.py --lint` is run, **Then** the script validates the two-layer structure, checks for dangling token references, and runs WCAG 2.2 AA contrast checks via `buddhi`'s contrast engine (`buddhi.scripts.contrast`), reporting any failing foreground/background pairs with exact luminance ratios.

---

### User Story 2 - Default Harness Scaffolding via `buddhi init` (Priority: P2)

When a user runs `buddhi init` on a new or existing repository, the `/design-md` skill (`.agents/skills/design-md/SKILL.md`, `scripts/detect_design_md.py`, and `references/design-md-spec.md`) is automatically scaffolded into `.agents/skills/design-md/` following Google Antigravity Customization System best practices (progressive disclosure, concise `SKILL.md` frontmatter, on-demand reference loading, and idempotent file syncing).

**Why this priority**: The user explicitly required that the skill be part of `buddhi init` initialization skills and optimized for Google Antigravity (`https://antigravity.google/docs/skills/` and `https://antigravity.google/docs/rules/`).

**Independent Test**: Run `buddhi init` on a clean temporary directory in `pytest`, assert that `.agents/skills/design-md/SKILL.md`, `.agents/skills/design-md/scripts/detect_design_md.py`, and `.agents/skills/design-md/references/design-md-spec.md` are created, and verify that running `buddhi init` a second time preserves any user customizations to those files.

**Acceptance Scenarios**:

1. **Given** an uninitialized directory, **When** `buddhi init` runs, **Then** `.agents/skills/design-md/SKILL.md`, `.agents/skills/design-md/scripts/detect_design_md.py`, and `.agents/skills/design-md/references/design-md-spec.md` are scaffolded into `.agents/` alongside existing initialization skills.
2. **Given** an initialized workspace where `.agents/skills/design-md/SKILL.md` has been customized by the user, **When** `buddhi init` is re-run, **Then** the customized file is left untouched (`kept_existing`).

---

### User Story 3 - SDD Workflow & Antigravity Specialist/Rule Integration (Priority: P3)

When a developer uses the Spec-Driven Development (SDD) workflow (`/specify`, `/spec-plan`, `/implement`, `/verify`) or dispatches `frontend-specialist` on a feature touching UI/frontend components, the harness checks for and consults `DESIGN.md` at the repository root. If UI/frontend work is planned in `/spec-plan` and `DESIGN.md` is missing or out of sync with codebase tokens, `/spec-plan` prompts or invokes `/design-md` (mirroring the `AGENTS.md` compliance check). Moreover, `.agents/rules/antislop.md` and `.agents/rules/a11y.md` reference `DESIGN.md` as the project's canonical visual & token contract without exceeding Antigravity's 24 KB per-file limit or 20,000-token aggregate rules budget.

**Why this priority**: Integrating `DESIGN.md` into the SDD lifecycle and Antigravity rules ensures agents actually read and enforce the design system during specification, planning, implementation, and verification rather than treating `DESIGN.md` as an isolated file.

**Independent Test**: Inspect `.agents/skills/specify/SKILL.md`, `.agents/skills/spec-plan/SKILL.md`, `.agents/skills/implement/SKILL.md`, `.agents/skills/verify/SKILL.md`, `.agents/agents/frontend-specialist.md`, `.agents/rules/antislop.md`, and `.agents/rules/a11y.md` (and their counterparts in `src/buddhi/templates/agents/`) to verify `DESIGN.md` gates and parity tests pass.

**Acceptance Scenarios**:

1. **Given** a UI/frontend feature in `/spec-plan`, **When** the agent synthesizes `plan.md`, **Then** it performs a `DESIGN.md` Compliance Check (verifying `DESIGN.md` tokens, vivid aesthetic direction, and WCAG 2.2 AA contrast, or recommending `/design-md` if missing/stale).
2. **Given** a repository with a root `DESIGN.md`, **When** `frontend-specialist`, `/implement`, or `/verify` executes on UI tasks, **Then** the agent consults `DESIGN.md` for aesthetic direction and design tokens and runs `detect_design_md.py --lint` during verification.

---

### User Story 4 - Documentation, Changelog & Attribution Updates (Priority: P4)

A user or contributor inspecting `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, and `README.md` finds complete, accurate documentation of the new `/design-md` skill under `[Unreleased]` in `CHANGELOG.md`, proper open-source attribution for Google Labs / Google Stitch `DESIGN.md` (`https://stitch.withgoogle.com/docs/design-md/specification` and `https://github.com/google-labs-code/design.md`, Apache-2.0) and Google Antigravity Skills/Rules docs in `ACKNOWLEDGMENTS.md`, and updated feature/skill descriptions in `README.md`.

**Why this priority**: Explicitly required by the prompt instructions (Instructions 2, 3, and 4) to maintain documentation and open-source attribution integrity.

**Independent Test**: Verify `CHANGELOG.md` under `## [Unreleased]`, `ACKNOWLEDGMENTS.md`, and `README.md` contain the required sections and valid links.

**Acceptance Scenarios**:

1. **Given** the repository root documentation files, **When** inspected after implementation, **Then** `CHANGELOG.md` documents the `/design-md` skill under `[Unreleased]`, `ACKNOWLEDGMENTS.md` credits the Google Stitch / Google Labs `DESIGN.md` specification (`https://github.com/google-labs-code/design.md` and `https://stitch.withgoogle.com/docs/design-md/specification`) and Antigravity docs, and `README.md` lists `/design-md` in the harness overview.

---

### Edge Cases

- **Backend-only or CLI-only repositories without CSS/UI files**: When `detect_design_md.py` runs on a project with zero CSS, Tailwind, or frontend files, it must not crash or invent fake framework dependencies; in default/JSON mode it reports `has_ui_surface: false`, and if `--apply` is explicitly requested by the user, it scaffolds a clean, minimal `DESIGN.md` template ready for prose and token customization.
- **Malformed YAML frontmatter or missing frontmatter in existing `DESIGN.md`**: If an existing `DESIGN.md` has only Markdown prose without `---` YAML frontmatter (or malformed YAML), the parser must gracefully extract the Markdown sections without losing a single line of user prose and prepend valid YAML frontmatter on merge.
- **CSS Variables with non-hex colors (e.g., `rgb()`, `hsl()`, `oklch()`, or CSS `var()` references)**: Contrast validation via `buddhi.scripts.contrast` supports hex and `rgb()`/`rgba()`; for unsupported color spaces or unresolved dynamic `var()` aliases, `--lint` must skip contrast math gracefully and emit an informational note rather than crashing.
- **Preserving vivid prose in `## Overview`**: Because the specification states that the vivid prose description (e.g., *"A graduate-level computer science lecture handout in the tradition of an old established university"*) is the most important layer of `DESIGN.md`, `merge_design_md` must never overwrite existing non-placeholder prose in `## Overview` unless `--aesthetic` is explicitly passed to update it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a Python package `src/buddhi/skills/design_md/` exposing `detect_design_facts`, `generate_design_md`, `merge_design_md`, `diff_design_md`, and `lint_design_md`.
- **FR-002**: The detector (`detect_design_facts`) MUST deterministically scan the project root (excluding `.git`, `node_modules`, `.venv`, `dist`, `build`, `.buddhi/site`) for design system evidence:
  - CSS / SCSS / PostCSS custom properties (`--color-*`, `--bg-*`, `--text-*`, `--surface-*`, `--border-*`, `--font-*`, `--radius-*`, `--spacing-*`, `--shadow-*`).
  - Tailwind CSS configurations (`tailwind.config.js`, `tailwind.config.ts`, `tailwind.config.mjs`, or Tailwind v4 `@theme` blocks).
  - Design token JSON files (`tokens.json`, `design-tokens.json`, `theme.json`, W3C DTCG `$value` tokens).
  - Frontend framework indicators in `package.json` or Python static theme templates.
- **FR-003**: The generator (`generate_design_md`) MUST produce a two-layer `DESIGN.md` document adhering to the Google Labs `DESIGN.md` specification:
  1. **Layer 1 — Machine-Readable YAML Frontmatter**: `name`, `version`, `aesthetic`, `colors`, `typography`, `spacing`, `rounded`, and `elevation`.
  2. **Layer 2 — Human-Readable Markdown Prose**:
     - `# Design System: <Project Name>`
     - `## Overview` (featuring the vivid aesthetic direction prose that paints a clear mental picture for AI coding agents, plus design philosophy bullets)
     - `## Colors` (semantic role breakdown explaining *why* and *where* each token is applied)
     - `## Typography` (font families, modular scale, weight hierarchy, and reading width constraints)
     - `## Layout` (grid system, container widths, spacing scale discipline)
     - `## Elevation & Depth` (shadows, borders, z-index layering philosophy)
     - `## Shapes` (corner radius scale and geometric consistency rules)
     - `## Components` (concrete guardrails for Buttons, Cards, Inputs, Navigation, and Modals)
     - `## Do's and Don'ts` (explicit positive and negative guardrails to prevent stateless AI visual drift)
- **FR-004**: The merger (`merge_design_md`) MUST parse both YAML frontmatter and Markdown sections (`#` / `##`), non-destructively updating machine-readable tokens while preserving hand-written prose in `## Overview`, `## Components`, `## Do's and Don'ts`, and any custom user sections byte-for-byte.
- **FR-005**: **Accessibility (A11Y) & Contrast Compliance**: The linter (`lint_design_md`) MUST integrate with `buddhi`'s WCAG 2.2 AA contrast engine (`buddhi.scripts.contrast`) and reference the `a11y` skill (`.agents/skills/a11y/SKILL.md`), verifying that:
  - Both layers (YAML frontmatter and required Markdown prose sections, especially a vivid `## Overview` and `## Do's and Don'ts`) are present and non-empty.
  - Semantic foreground/background token pairs (`primary` on `surface`/`background`, `text` on `surface`/`background`, `secondary` on `surface`/`background`) satisfy WCAG 2.2 AA contrast ratios (minimum `4.5:1` for normal text, `3.0:1` for large text / UI components).
  - Generated `## Components` and `## Do's and Don'ts` sections mandate keyboard operability, visible `:focus-visible` indicators, and semantic HTML landmarks per `.agents/rules/a11y.md`.
- **FR-006**: System MUST provide a cross-platform CLI helper script `.agents/skills/design-md/scripts/detect_design_md.py` supporting `--root`, `--diff`, `--apply`, `--lint`, `--json`, and `--aesthetic "<vivid prose description>"`.
- **FR-007**: System MUST bundle the `/design-md` skill (`.agents/skills/design-md/SKILL.md`, `scripts/detect_design_md.py`, and `references/design-md-spec.md`) in both `.agents/skills/design-md/` and `src/buddhi/templates/agents/skills/design-md/` so `buddhi init` scaffolds it automatically and idempotently.
- **FR-008**: The `/design-md` skill MUST adhere to Google Antigravity Customization System best practices (`https://antigravity.google/docs/skills/` and `https://antigravity.google/docs/rules/`):
  - Concise `SKILL.md` with lowercase hyphenated `name: design-md` and clear third-person trigger `description`.
  - Progressive disclosure placing detailed `DESIGN.md` specification examples and archetype prose gallery in `references/design-md-spec.md`.
  - Rule integration keeping all `.agents/rules/*.md` files well under the 24 KB per-file cap and 20,000-token aggregate rules budget.
- **FR-009**: SDD skills (`/specify`, `/spec-plan`, `/implement`, `/verify`), `frontend-specialist`, `.agents/rules/antislop.md`, and `.agents/rules/a11y.md` (in both `.agents/` and `src/buddhi/templates/agents/`) MUST be updated to consult `DESIGN.md` and invoke `/design-md` when UI/frontend work is planned or verified.
- **FR-010**: `CHANGELOG.md` MUST be updated under `## [Unreleased]`, `ACKNOWLEDGMENTS.md` MUST be updated with references to the Google Stitch / Google Labs `DESIGN.md` specification and Google Antigravity docs, and `README.md` MUST be updated to document `/design-md`.

### Key Entities

- **`DesignTokens`**: Machine-readable token dictionary extracted from or written to `DESIGN.md` YAML frontmatter (`colors`, `typography`, `spacing`, `rounded`, `elevation`).
- **`DesignFacts`**: Repository design system metadata discovered by `detect_design_facts` (`name`, `aesthetic`, `has_ui_surface`, `framework`, `source_files`, `tokens`).
- **`DesignSection`**: Parsed Markdown section (`heading`, `level`, `content`, `is_managed`) used for non-destructive section-aware merging.
- **`ContrastFinding`**: Result of evaluating a foreground/background color token pair (`fg_key`, `fg_hex`, `bg_key`, `bg_hex`, `ratio`, `passes_aa`, `passes_large_aa`).
- **`DesignLintReport`**: Structured validation output (`is_valid`, `errors`, `warnings`, `contrast_findings`, `missing_sections`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `detect_design_md.py --apply` generates a spec-compliant two-layer `DESIGN.md` file (valid YAML frontmatter + all 8 canonical Markdown prose sections) in under 1 second with zero external network calls.
- **SC-002**: Merging updates into an existing `DESIGN.md` preserves 100% of custom user sections and custom `## Overview` / `## Do's and Don'ts` prose byte-for-byte.
- **SC-003**: `detect_design_md.py --lint` accurately flags missing canonical sections, malformed YAML frontmatter, and WCAG 2.2 AA color token contrast violations (`< 4.5:1` for text/surface pairs).
- **SC-004**: `buddhi init` scaffolds `.agents/skills/design-md/` (`SKILL.md`, `scripts/detect_design_md.py`, `references/design-md-spec.md`) idempotently, verified by automated `pytest` tests.
- **SC-005**: Template parity between `.agents/` and `src/buddhi/templates/agents/` passes 100%, and all new Python modules remain strictly below the 8,000-token file size ratchet (`buddhi scripts check-file-size`).

## Assumptions

- `DESIGN.md` lives at the root of a repository (`<root>/DESIGN.md`), matching the Google Labs `google-labs-code/design.md` specification.
- `buddhi init` scaffolds the `/design-md` skill into `.agents/skills/design-md/` for all projects, while the actual root `DESIGN.md` file is generated on demand when the user runs `/design-md` or when `/spec-plan` detects UI/frontend work.
- All implementation code in `src/buddhi/skills/design_md/` uses Python 3.10+ standard library plus existing `buddhi-cli` dependencies (`pyyaml` / stdlib parser and `buddhi.scripts.contrast`), requiring zero new third-party dependencies.
