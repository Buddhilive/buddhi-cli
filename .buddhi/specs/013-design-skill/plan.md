# Implementation Plan: DESIGN.md Skill & Design System Codification (`/design-md`)

**Branch**: `013-design-skill` | **Date**: 2026-10-30 | **Spec**: [.buddhi/specs/013-design-skill/spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/013-design-skill/spec.md)

**Input**: Feature specification from `/.buddhi/specs/013-design-skill/spec.md`

## Summary

Implement the `/design-md` skill and Python engine in `buddhi-cli` to codify, update, and validate a repository's `DESIGN.md` design system contract based on the open-source Google Labs / Google Stitch specification (`https://stitch.withgoogle.com/docs/design-md/specification`, `https://github.com/google-labs-code/design.md`). The engine extracts machine-readable design tokens from CSS variables, Tailwind configurations, and token JSON into YAML frontmatter, creates and non-destructively preserves vivid aesthetic direction prose across 8 canonical Markdown sections, validates foreground/background color token pairs against WCAG 2.2 AA contrast standards using `buddhi.scripts.contrast`, scaffolds automatically and idempotently via `buddhi init`, and integrates tightly with the Spec-Driven Development (SDD) lifecycle and Google Antigravity specialist agents and rules.

## Technical Context

**Language/Version**: Python >= 3.10  
**Primary Dependencies**: `pyyaml>=6.0` (existing in `pyproject.toml`), Python standard library (`re`, `json`, `difflib`, `pathlib`, `dataclasses`, `argparse`, `sys`), and internal module `buddhi.scripts.contrast` for WCAG 2.2 AA contrast math. Zero new external dependencies.  
**Storage**: File system (`DESIGN.md` at project root, `.agents/skills/design-md/` for skill runbook, script, and references).  
**Testing**: `pytest` (`uv run pytest tests/skills/test_design_md.py`) covering token detection, two-layer generation, non-destructive section merging, WCAG contrast linting, and `buddhi init` idempotency.  
**Target Platform**: Cross-platform (Windows, macOS, Linux).  
**Project Type**: CLI tool & Agent Harness Generator.  
**Performance Goals**: `detect_design_md.py --apply` and `--lint` execute in `< 1.0s` on typical repos without external network requests.  
**Constraints**: All Python source files must remain strictly under the 8,000-token ratchet ceiling (`buddhi scripts check-file-size`). Rules must adhere to Antigravity's 24 KB per-file limit and 20,000-token aggregate rules budget.  
**Scale/Scope**: 5 modular Python files under `src/buddhi/skills/design_md/`, 1 CLI script under `.agents/skills/design-md/scripts/`, 1 Antigravity skill `SKILL.md`, 1 specification reference guide `design-md-spec.md`, mirror templates under `src/buddhi/templates/agents/`, SDD skill updates (`specify`, `spec-plan`, `implement`, `verify`), rule updates (`antislop.md`, `a11y.md`), and comprehensive tests.

## AGENTS.md Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Project build & test commands adhered to (`uv run pytest`, `uv run ruff check .`, `uv run mypy src/ tests/`)
- [x] Architectural constraints respected (pure Python stdlib + existing `pyyaml` and `buddhi.scripts.contrast`, idempotency in `buddhi init`, token ratchet under 8,000 tokens)
- [x] No unapproved external dependencies introduced (zero new dependencies added to `pyproject.toml`)

## Project Structure

### Documentation & Spec Artifacts

```text
.buddhi/specs/013-design-skill/
├── spec.md              # Feature specification
├── plan.md              # This file (/spec-plan output)
└── tasks.md             # Task breakdown (/spec-tasks output)
```

### Source Code & Template Layout

```text
src/buddhi/skills/design_md/
├── __init__.py          # Public exports (detect_design_facts, generate_design_md, merge_design_md, diff_design_md, lint_design_md)
├── models.py            # Dataclasses: DesignTokens, DesignFacts, DesignSection, ContrastFinding, DesignLintReport, MergeResult
├── detector.py          # Fact & token scanner (CSS vars, Tailwind configs, token JSON, framework indicators)
├── generator.py         # Two-layer DESIGN.md builder (YAML frontmatter + 8 canonical Markdown sections)
├── merger.py            # Non-destructive section parser, frontmatter updater, byte-for-byte custom prose preservation
└── linter.py            # Structural validator & WCAG 2.2 AA contrast checker via buddhi.scripts.contrast

.agents/skills/design-md/
├── SKILL.md             # Antigravity skill definition with YAML frontmatter and progressive disclosure
├── scripts/
│   └── detect_design_md.py  # Standalone CLI helper script (--diff, --apply, --lint, --json, --aesthetic, --root)
└── references/
    └── design-md-spec.md    # Two-layer spec guide, token schema, and vivid aesthetic direction archetypes

src/buddhi/templates/agents/skills/design-md/
├── SKILL.md             # Packaged template for buddhi init
├── scripts/
│   └── detect_design_md.py  # Packaged helper script for buddhi init
└── references/
    └── design-md-spec.md    # Packaged spec reference for buddhi init

tests/skills/
└── test_design_md.py    # Test suite: detection, generation, merging, contrast linting, init idempotency
```

## Architectural Design & Components

### 1. Two-Layer Architecture of `DESIGN.md`

`DESIGN.md` combines machine-readable tokens with human-readable rationale:

$$\text{DESIGN.md} = \langle \mathcal{T}_{\text{tokens}}, \mathcal{R}_{\text{rationale}} \rangle$$

1. **Layer 1: YAML Front Matter (`\mathcal{T}_{\text{tokens}}`)**:
   Contains strict, machine-readable design tokens:
   - `name`, `version`, `aesthetic` (one-line vivid mental picture), `dials` (`energy`, `rhythm`, `motion`).
   - `colors`: Semantic roles (`background`, `surface`, `surface-elevated`, `text`, `text-muted`, `primary`, `primary-foreground`, `secondary`, `secondary-foreground`, `accent`, `accent-foreground`, `border`, `destructive`).
   - `typography`: `fonts` (`sans`, `serif`, `mono`), `scale` (`xs` to `3xl`), `weights`, `reading-width` (`65ch`).
   - `spacing`: `base` (`4px`), `scale` (`1` through `16`), `container` boundaries.
   - `rounded`: `none`, `sm`, `md`, `lg`, `full`.
   - `elevation`: `none`, `sm`, `md`, `lg`.

2. **Layer 2: Markdown Prose Rationale (`\mathcal{R}_{\text{rationale}}`)**:
   Contains the human rationale and guardrails across the 8 canonical sections:
   - `# Design System: <Project Name>`
   - `## Overview`: Vivid aesthetic direction prose (the most important section that sets the tone for AI agents—e.g., *"A graduate-level computer science lecture handout in the tradition of an old established university"*) + Core design philosophy bullets.
   - `## Colors`: Semantic role explanations, token table, and contrast ratios.
   - `## Typography`: Type families, scale hierarchy, line-length discipline.
   - `## Layout`: Grid containers, spacing scale multiples.
   - `## Elevation & Depth`: Shadow usage, borders-as-depth, z-index hierarchy.
   - `## Shapes`: Corner radius consistency (preventing mixed rounded/sharp styles).
   - `## Components`: Specific design contracts for Buttons, Cards, Inputs, Navigation, and Modals with `:focus-visible` states.
   - `## Do's and Don'ts`: Actionable positive and negative rules stopping generic AI slop.

### 2. Detection Engine (`detector.py`)

- **Scanner**: Walks repository root (excluding `.git`, `node_modules`, `.venv`, `dist`, `build`, `.buddhi/site`, `__pycache__`).
- **Surface Parsers**:
  - **CSS/SCSS custom properties**: Regex matches `--color-*`, `--bg-*`, `--text-*`, `--font-*`, `--spacing-*`, `--radius-*`, `--shadow-*` within `:root` or `@theme` blocks.
  - **Tailwind CSS**: Analyzes `tailwind.config.*` (JS/TS/MJS/CJS) and Tailwind v4 `@theme` directives for custom color palettes, font families, and border radiuses.
  - **Design Token JSON**: Parses `tokens.json`, `design-tokens.json`, `theme.json`, and W3C DTCG `$value` objects.
  - **Package Manifest**: Checks `package.json` dependencies for UI libraries (Tailwind, Radix, shadcn, MUI, React, Vue, Svelte).
- **Graceful Fallback**: If no frontend files are found (`has_ui_surface = False`), emits an accessible neutral design token set (zinc/slate palette, system sans, 4px scale) so a starter `DESIGN.md` can be generated cleanly on demand.

### 3. Non-Destructive Merger (`merger.py`)

- **Section-Aware Parsing**:
  - Splits `DESIGN.md` into YAML frontmatter and Markdown sections using regex `^(#{1,3})\s+(.+)$`.
  - Classifies sections as managed (`Overview`, `Colors`, `Typography`, `Layout`, `Elevation & Depth`, `Shapes`, `Components`, `Do's and Don'ts`) or unmanaged custom user sections.
- **Merge Invariants**:
  - **YAML Frontmatter**: Updates detected tokens while preserving custom metadata fields and existing `aesthetic` prose unless an explicit `--aesthetic` override is provided.
  - **`## Overview`**: Hand-crafted aesthetic prose is preserved byte-for-byte; placeholder prose is updated if `--aesthetic` is provided.
  - **Managed Token Tables (`## Colors`, `## Typography`)**: Token tables are regenerated to reflect codebase reality.
  - **Custom User Sections**: Any custom sections (e.g. `## Brand Voice`, `## Iconography`) are preserved 100% byte-for-byte in their original position.
  - **Diff Engine**: Computes unified diff via `difflib.unified_diff` for review.

### 4. Accessibility Strategy & Contrast Linter (`linter.py`)

- **WCAG 2.2 AA Contract**:
  - Integrates directly with `buddhi.scripts.contrast` (`contrast_ratio`, `parse_color_extended`, `composite`).
  - Evaluates standard semantic pairs:
    1. `text` on `background` (>= `4.5:1`)
    2. `text` on `surface` (>= `4.5:1`)
    3. `text-muted` on `background` and `surface` (>= `4.5:1` normal, >= `3.0:1` large/auxiliary)
    4. `primary-foreground` on `primary` (>= `4.5:1` or `3.0:1` for bold >=18px)
    5. `secondary-foreground` on `secondary` (>= `4.5:1`)
    6. `accent-foreground` on `accent` (>= `4.5:1`)
    7. `border` on `background` / `surface` (>= `3.0:1` for UI control boundaries)
- **Diagnostic Output**:
  - Reports per-pairing ratios and pass/fail status.
  - Handles dynamic `var(...)` or unparseable color strings by emitting informative warning notes without throwing unhandled exceptions.
  - Verifies presence of all 8 canonical sections and structural validity of YAML frontmatter.

### 5. Google Antigravity & SDD Integration

- **Google Antigravity Customization Architecture**:
  - `.agents/skills/design-md/SKILL.md` conforms to Antigravity skill specification with lowercase hyphenated name, clear third-person description, and progressive disclosure linking to `references/design-md-spec.md`.
  - `.agents/skills/design-md/scripts/detect_design_md.py` provides cross-platform CLI execution with dual-path import handling.
  - Scaffolded into `.agents/skills/design-md/` by `buddhi init` via `sync_template_tree`, preserving any existing user customizations (`kept_existing`).
- **SDD Lifecycle Integration**:
  - `/spec-plan`: Incorporates `DESIGN.md` Compliance Check in `plan.md` template and execution; prompts `/design-md` if UI surfaces are touched and `DESIGN.md` is missing or out of sync.
  - `frontend-specialist`: References `DESIGN.md` as the primary design system and visual token contract.
  - `/specify`: Recommends defining aesthetic intent and referencing `DESIGN.md` for UI user stories.
  - `/implement`: Mandates adhering to `DESIGN.md` tokens and aesthetic prose.
  - `/verify`: Runs `detect_design_md.py --lint` as part of UI verification gates.
- **Rule Integration**:
  - Updates `.agents/rules/antislop.md` and `.agents/rules/a11y.md` (and their counterparts in `src/buddhi/templates/agents/rules/`) to reference `DESIGN.md` as the visual and accessibility anchor, keeping all rule files well under the 24 KB per-file limit and 20,000-token rules budget.

### 6. Documentation, Changelog & Attribution

- **Changelog**: Add detailed entry under `## [Unreleased]` in `CHANGELOG.md` documenting `/design-md`, token detection, non-destructive merging, WCAG contrast linting, and Antigravity/SDD integration.
- **Acknowledgments**: Update `ACKNOWLEDGMENTS.md` with full attribution for:
  - Google Labs / Google Stitch `DESIGN.md` specification (`https://stitch.withgoogle.com/docs/design-md/specification` and `https://github.com/google-labs-code/design.md`, Apache-2.0).
  - Google Antigravity Customization System documentation (`https://antigravity.google/docs/skills/` and `https://antigravity.google/docs/rules/`).
- **README**: Update `README.md` to list the `/design-md` skill and explain `DESIGN.md` design system codification.

## Complexity Tracking

| Module / Area | Risk / Complexity | Mitigation |
| :--- | :--- | :--- |
| CSS & Tailwind Token Extraction | Medium (variety of Tailwind configurations and CSS formats) | Bounded scanning with regex fallbacks and robust DTCG JSON parsing; emit clean fallback tokens when detection yields partial sets. |
| Non-destructive Section Merging | Medium (user-edited prose preservation) | Two-layer parsing separating YAML frontmatter from Markdown body; strict regex section splitting preserving custom headings and body text byte-for-byte. |
| WCAG Contrast Checking | Low-Medium (handling alpha composite and non-hex colors) | Reuse battle-tested `buddhi.scripts.contrast` module (`contrast_ratio`, `parse_color_extended`, `composite`); skip dynamic CSS variables with clear warning. |
| Antigravity Rule & Size Limits | Low | Modular file decomposition keeping all files < 300 lines (< 2,500 tokens), well within the 8,000-token ratchet; rules remain concise pointers. |
| `buddhi init` Scaffolding | Low | Use established `sync_template_tree` mechanism; idempotent without overwriting existing files. |

## Verification Plan

1. **Unit & Integration Tests (`tests/skills/test_design_md.py`)**:
   - `test_detect_facts_css_variables`: Scans fixture with `:root` CSS variables and extracts color, typography, and spacing tokens.
   - `test_detect_facts_tailwind_config`: Scans fixture with `tailwind.config.js` and extracts theme extensions.
   - `test_detect_facts_no_ui_fallback`: Confirms fallback token generation for backend/CLI projects.
   - `test_generate_two_layer_design_md`: Verifies valid YAML frontmatter and all 8 canonical Markdown sections.
   - `test_merge_preserves_custom_prose`: Confirms that custom `## Overview` prose and custom sections (`## Brand Voice`) are preserved byte-for-byte during token updates.
   - `test_linter_wcag_contrast_pass_and_fail`: Verifies that compliant pairs pass and failing pairs (`< 4.5:1`) are reported with exact luminance ratios.
   - `test_init_scaffolds_design_md_skill_idempotent`: Runs `buddhi init` on a temporary directory and verifies that `.agents/skills/design-md/` is created and preserved on repeat runs.
2. **Quality & Formatting Gates**:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/ tests/`
   - `uv run pytest tests/skills/test_design_md.py`
   - `uv run buddhi scripts check-file-size` (verifying token ratchet ceiling).
