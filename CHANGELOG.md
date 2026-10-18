# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **A11Y.md Accessibility Framework Integration**:
  - Adapted the `A11Y.md` framework ([https://github.com/fecarrico/A11Y.md](https://github.com/fecarrico/A11Y.md), Felipe A. Carriço) into the Google Antigravity harness and Spec-Driven Development (SDD) workflow initialized via `buddhi init`.
  - **`a11y` Skill & Modular Guides (`.agents/skills/a11y/`)**:
    - Created the `a11y` skill packaging all 31 specialized pattern reference guides (`guide-*.md`) covering buttons, forms, modal dialogs, media, navigation, and touch targets with a token-efficient index and lazy-loading protocol.
    - Added templates for release evidence (`REPORT.md`), unresolvable technical exceptions (`EXCEPTIONS.md`), cross-turn pattern memory (`A11Y-DECISIONS.md`), and public accessibility statements (`ACCESSIBILITY.md`).
  - **Always-on Rule (`.agents/rules/a11y.md`)**:
    - Installed always-on routing rule enforcing WCAG 2.2 AA / EN 301 549 standards, mandatory semantic HTML over ARIA recreation, and cross-turn pattern memory lookups.
  - **Deterministic Static Gate (`buddhi scripts verify-a11y`)**:
    - Created pure Python 3.10+ stdlib modular verification package (`src/buddhi/scripts/verify_a11y/`) keeping all files within the 8,000-token ratchet budget.
    - Audits 11 source anti-patterns: `clickable-div`, `placeholder-label`, `half-climbed-aria`, `aria-soup`, `nullified-alt`, `orphaned-aria`, `overlay`, `positive-tabindex`, `outline-none`, `redundant-alert`, and `media-autoplay`.
    - Verifies release evidence freshness, completeness, contrast table math recomputation, and verification independence (`cross-agent`, `fresh-context`, `self-reported`).
    - Added `--warn-only` and fixture self-test (`--selftest`) passing 31 test scenarios.
  - **Enhanced Contrast Engine (`buddhi scripts contrast`)**:
    - Extended the contrast CLI to support multi-pair evaluation (`--bg`, `--fg`), strictness profiles (`standard`, `shield`, `launchpad`), alpha compositing over page background, and CSS stylesheet triage (`--css`, `--page-bg`).
  - **FastMCP Tools**:
    - Registered `verify_a11y` on the Buddhi MCP server with structured JSON output option (`as_json=True`).
    - Enhanced `check_contrast` to accept background/foreground tokens, strictness profiles, and CSS file triage paths.
  - **SDD Integration & Memory Promotion**:
    - Integrated A11Y checkpoints and guidance into `frontend-specialist`, `/specify`, `/spec-plan`, `/spec-tasks`, `/implement`, `/verify`, and `/close-spec`.
    - Added automatic extraction of `A11Y-DECISIONS.md` pattern memory into durable OKF concept nodes (`mem-decision-a11y-*`) via `buddhi memory sdd-promote`.
  - Updated `ACKNOWLEDGMENTS.md` with complete attribution and MIT license text for `A11Y.md`.
- **OKF v0.2 & Claude Code Memory Layer**:
  - Implemented a deterministic project-level memory architecture combining **Google Open Knowledge Format (OKF v0.2)** concept schemas and **Claude Code Memory** standards into the Google Antigravity agent harness scaffolded by `buddhi init`.
  - **Memory Bundle Storage Engine (`src/buddhi/memory/`)**:
    - Atomic concept nodes with strict YAML frontmatter (`id`, `kind`, `title`, `summary`, `status`, `confidence`, `scope`, `paths`, `tags`, `sources`, `relations`).
    - Multi-scope memory hierarchy: `project` (`.agents/memory/`), `local` (`.agents/memory.local/`), `user` (`~/.buddhi/memory/`), and specialist subagent memory (`.agents/agent-memory/<agent>/`).
    - Strict context budget enforcement: root `MEMORY.md` capped at `<= 200 lines` and `<= 25,600 bytes` (25 KB) with `<= 150 char` pointer lines, backed by compaction demotion into `<topic>/index.md`.
    - Provenance hashing and staleness detection: SHA-256 computation over full files or `#L<start>-L<end>` line ranges with CRLF->LF cross-platform normalization.
    - Path-scoped activation: glob matching (`paths: [...]`) using `pathspec` gitignore rules against active session files.
    - Recursive `@path` imports: sandboxed inline expansion up to a maximum depth of 5 hops with cycle detection and workspace boundary validation.
    - Security invariants: directory traversal guards, secret and token leakage scanners, slug sanitization, and safe YAML parsing.
    - SDD Promotion engine: automatic extraction of durable decisions and verified sound choices from `.buddhi/specs/<branch>/` into OKF concept nodes.
    - Non-destructive legacy migration: automatically migrates legacy unformatted topic files (`user-preferences.md`, etc.) to OKF concept files and backs up originals as `.md.bak`.
  - **`buddhi memory` CLI Command Group**:
    - `buddhi memory status`: Real-time budget utilization, stale concept reporting, and broken relation telemetry.
    - `buddhi memory add`: Deterministic concept node creation with automated SHA-256 source hashing.
    - `buddhi memory search`: Query search across scopes with active file path glob filtering.
    - `buddhi memory read`: Reads memory concept nodes with optional recursive `@path` expansion.
    - `buddhi memory validate`: Bundle conformance, line/byte cap, and source hash verification.
    - `buddhi memory sync`: Reconciles topic `index.md` files and root `MEMORY.md`.
    - `buddhi memory compact`: Prunes and demotes lower-priority entries to keep `MEMORY.md` within the 200-line budget.
    - `buddhi memory migrate`: Converts legacy flat files to OKF concept nodes.
    - `buddhi memory sdd-promote`: Extracts spec choices into OKF decisions.
  - **`buddhi_memory` MCP Tool**:
    - Registered on the `buddhi-mcp` FastMCP server, allowing AI coding agents to search, read, remember, and check memory status over StdIO.
  - **Antigravity Harness & SDD Integration**:
    - Added `/memory` skill for interactive inspection, staleness auditing, and compaction.
    - Upgraded `/remember` and `/status` skills to leverage OKF concept schemas and `buddhi memory`.
    - Integrated memory discovery and staleness checks into `/spec-plan`, `/specify`, and `/close-spec`.
    - Updated specialist agent definitions (`backend-specialist`, `frontend-specialist`, `database-specialist`, etc.) with `memory: project` frontmatter.
  - Updated `ACKNOWLEDGMENTS.md` to credit Claude Code Memory documentation and Google Open Knowledge Format (OKF).
- **Software Factory Skills & Scripts Adaptation (`dzhng/skills`)**:
  - Integrated 23 SDD-complementary agent skills adapted from `dzhng/skills` into the default Google Antigravity harness scaffolded by `buddhi init`:
    - *Discovery & Research*: `explore-unknowns` (4-quadrant unknown mapping with 6 stage reference guides), `auto-research` (progressive hypothesis testing & parameter-effect maps in `.buddhi/specs/<branch>/research.md`).
    - *Implementation, Refactoring & Testing*: `refactor-clean` (clean structural refactoring without legacy shims), `write-tests` (tracer-bullet behavioral test authoring), `audit-tests` (contract boundary mapping), `audit-performance` (bounded-work runtime efficiency checks), `ratchet-files` (source file size ceiling enforcement), `write-docs` (principles and pointers markdown documentation), `marketing-pages` (marketing site architecture and audits).
    - *Review, Decision Audit & Spec Closeout*: `code-review` (26-point diff review checklist), `review` (sequenced closeout: shape -> diff -> docs), `audit-choices` (triages unprompted agent choices into `.buddhi/specs/<branch>/choices.md` as sound, unsound, needs-user), `handoff-spec` (mid-implementation state capture), `close-spec` (post-verification archival into `.buddhi/specs/done/<branch>/` as durable architectural rationale), `eli5` (plain-language walkthrough of any spec or diff), `retro` (session retrospective emphasizing automated checks over prose rules).
    - *Visual Review*: `design-with-images` (visual concept generation via Antigravity `image-generator`), `compare-screenshots` (telemetry and reference-vs-candidate parity diffing), `screenshot-critique` (unprimed subagent visual checks), `preview-shots` (cross-platform image viewing).
    - *Authoring*: `write-skills` (skill authoring rulebook), `eval-skills` (subagent skill evaluation), `audit-agents` (AGENTS.md longevity and iteration speed audit).
  - Enhanced the 5 existing SDD lifecycle skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`) with software-factory practices (fog-of-war slicing, multi-angle slice checks, maintenance checkpoints, `/review`, `/audit-choices`, visual verification gates, `/close-spec` spec archiving) without replacing or altering the core SDD workflow.
  - Added pure-Python CLI scripts under `buddhi scripts`:
    - `buddhi scripts check-file-size`: Git-tracked source file token ratchet (default 8,000 tokens / 32 KB) supporting `--all`, staged pre-commit ratcheting against `HEAD`, and `@ratchet-files-ignore` headers.
    - `buddhi scripts visual-parity-diff`: Pure Python PNG codec (types 0-6, filters 0-4), solo scene-metrics telemetry, and pair diffing with 8 diagnostic PNG artifacts.
    - `buddhi scripts receipts`: Deterministic critique report verifier checking execution receipt blocks against prose measurement claims and SHA-256 artifact hashes.
    - Added `--selftest` flags to all 3 scripts.
  - Updated `ACKNOWLEDGMENTS.md` to credit `https://github.com/dzhng/skills` (David Zhang, MIT License) and upstream contributors (Matt Pocock, Thariq).
- **Anti-Slop Filter Integration**:
  - Integrated the `anti-slop` filter suite adapted from `miqdadbadjuber/anti-slop` into the default Google Antigravity agent harness created by `buddhi init`.
  - Added 6 specialized agent skills under `.agents/skills/`:
    - `antislop`: Core filter and two usage modes (`during`, `after`, `ask`).
    - `antislop-ui`: UI & visual design filter for layout, color, components, and motion.
    - `antislop-copywriting`: Copy & text filter against generic AI prose and synthetic marketing phrasing.
    - `antislop-human`: Human accessibility filter covering WCAG AA color contrast, focus rings, keyboard navigation, and touch targets.
    - `antislop-layoutmobile`: Responsive and mobile layout filter for viewport reflow, fluid scaling, and thumb tap targets.
    - `antislop-code`: Code comment hygiene filter eliminating redundant or narrating AI comments while preserving domain rationale.
  - Added always-on rule `.agents/rules/antislop.md` directing agents to load matching anti-slop skills during interface, copy, and code tasks.
  - Added `buddhi scripts` CLI command group:
    - `buddhi scripts contrast <color_a> <color_b>`: Standalone WCAG 2.x color contrast checker with pass/fail exit codes for normal (4.5:1) and large (3:1) text.
    - `buddhi scripts contrast --selftest`: Validates the bundled reference contrast table against the mathematical WCAG luminance formulas.
    - `buddhi scripts antislop-mode [during|after|ask]`: Inspects or configures the global anti-slop usage mode in the platform configuration file.
  - Added `check_contrast` tool to the Buddhi MCP server (`buddhi-mcp`), allowing agents to calculate WCAG color contrast directly during UI planning and review.
  - Added `ACKNOWLEDGMENTS.md` at project root providing attribution and full MIT license text for `miqdadbadjuber/anti-slop`.
- **Workflows to Skills Migration**:
  - Migrated all agent workflows (`.agents/workflows/*.md`) into native Google Antigravity Agent Skills under `.agents/skills/<name>/SKILL.md`.
  - Added standard YAML frontmatter (`name`, `description`) to all skills for autonomous agent discovery and slash-command invocation.
  - Provided automatic backward compatibility during `buddhi init` via `migrate_legacy_workflows()`:
    - Scans existing project `.agents/workflows/` directories.
    - Generates corresponding `skills/<name>/SKILL.md` while safely preserving any existing user customizations.
    - Archives migrated workflow files with `.md.bak` extensions.
    - Cleans up legacy entries in `.agents/workflows.json`.

### Changed
- **Slash Command Renaming (`/plan` to `/spec-plan`)**:
  - Renamed the Spec-Driven Development (SDD) planning skill from `plan` to `spec-plan` (`/spec-plan`) to resolve command collisions with Google Antigravity's built-in `/plan` slash command.
  - Implemented automatic legacy migration via `migrate_legacy_plan_skill()` during `buddhi init` to transition `.agents/skills/plan` into `.agents/skills/spec-plan` and update internal references without disrupting existing user customizations.
  - Preserved underlying architecture artifacts and CLI helpers (`plan.md`, `plan-template.md`, `buddhi sdd setup-plan`, `buddhi docs plan`).
- Updated agent harness rules (`harness-core.md`, `AGENTS.md`) and skill instructions (`specify`, `implement`, `tasks`) to reference `/spec-plan`.
- Updated documentation and README to reflect the skills architecture and the `/spec-plan` command.

## [1.0.0-beta.11] - 2026-09-13

### Added
- **Custom Agent Skills CLI (`buddhi skills`)**:
  - Added `buddhi skills` CLI command to inspect and manage custom agent skills.
  - Implemented `repo-to-skill` skill installer (`buddhi skills --repo-to-skill`) allowing agents to analyze repositories and generate reusable agent skills.
  - Added skills registry, installer, reference schemas, and unit test suite.
- **Codebase Q&A Skill (`/ask`)**:
  - Added conversational `/ask` workflow allowing agents to answer structural and architectural questions grounded in the code graph using `buddhi_search` and `buddhi_read` without modifying files.

### Changed
- Optimized SDD workflow execution and prerequisite checking across `/specify`, `/tasks`, `/quick-plan`, and `/debug`.
- Refined MCP server tool options and error handling.

## [1.0.0-beta.10] - 2026-08-28

### Added
- **Model Context Protocol (MCP) Server (`buddhi-mcp`)**:
  - Added `buddhi-mcp` Stdio server entrypoint and `buddhi mcp` CLI command for AI agent interaction.
  - Implemented `buddhi_search` tool: topology-aware code graph search using lexical anchors, Leiden community clustering, Shannon entropy boilerplate filtering, and token-budget-aware U-curve positional layout.
  - Implemented `buddhi_read` tool: AST-pruned, token-budgeted reading supporting multiple compression modes (`auto`, `signatures`, `map`, `entropy`, `full`).
  - Added `.agents/mcp_config.json` workspace configuration linking Antigravity directly to the workspace server.
  - Added `okf-context` skill and harness rules directing agents to consult MCP code graph tools before raw file grepping.

### Fixed
- Fixed global MCP configuration coupling by anchoring database and path resolution directly to repository workspace roots.

## [1.0.0-beta.9] - 2026-08-28

### Added
- **Spec-Driven Development (SDD) Lifecycle**:
  - Introduced end-to-end SDD workflows:
    - `/specify` — Scaffold feature specifications with prioritized, testable user stories.
    - `/plan` — Multi-specialist architectural planning grounded in the code graph.
    - `/tasks` — Story-oriented task breakdown with parallelism markers (`[P]`).
    - `/implement` — Prerequisite-enforced task execution and live checklist tracking.
    - `/verify` — Evidence-based test verification mapped to user story acceptance criteria (SDD convergence mode).
  - Added lightweight non-SDD planning workflow (`/quick-plan`) for smaller changes.
  - Added standard templates: `spec-template.md`, `plan-template.md`, `tasks-template.md`, `checklist-template.md`, and `agents-template.md`.
  - Added `buddhi sdd` CLI commands: `create`, `setup-plan`, `setup-tasks`, `check`, and `resolve-template`.

## [1.0.0-beta.8] - 2026-08-23

### Added
- **Mechanical Safety Hook (`guard_destructive.py`)**:
  - Implemented `PreToolUse` safety hook via `.agents/hooks.json` mechanically blocking destructive commands (force-push, `reset --hard`, table drops/truncations, root deletions) unless confirmed with explicit `CONFIRMED` marker string.
- **Systematic Harness Workflows**:
  - Added `/debug` workflow for root-cause diagnosis without modifying code.
  - Added `/verify` workflow for capturing genuine build/test output via `terminal-runner`.
  - Added `/remember` workflow for capturing user preferences, conventions, and architectural decisions.
  - Added `/status` workflow for quick harness health reporting.
- **Skills & Memory Indexing**:
  - Added `system-design` skill for evaluating architectural trade-offs during planning.
  - Split agent memory into categorized topic files (`user-preferences.md`, `project-conventions.md`, `tech-decisions.md`, `feedback-history.md`) under `.agents/memory/` indexed by `MEMORY.md`.

### Fixed
- Fixed recursive removal regex in safety hook to handle flags between command and target paths.
- Fixed template synchronization in `fsutil.py` to copy non-markdown files.

## [1.0.0b7] - 2026-08-22

### Added
- Automated PyPI publishing workflow via GitHub Actions (`publish.yml`) using PyPI trusted publishing (OIDC).
- Added MIT license, classifiers, author metadata, and repository links to package metadata.

### Changed
- Improved code documentation generation order and staleness tracking in `.buddhi/docs-plan.json`.

## [1.0.0b6] - 2026-08-22

### Added
- **Antigravity Full-Stack Agent Harness**:
  - Scaffolding of `.agents/` with domain specialist subagents (`backend-specialist`, `frontend-specialist`, `database-specialist`, `testing-specialist`, `security-specialist`, `deployment-specialist`, `git-specialist`) and `terminal-runner`.
  - Standard `AGENTS.md` root conventions file.
- **RepoAgent-Inspired Documentation Generator**:
  - Bottom-up, dependency-aware Open Knowledge Format (OKF) codebase documentation under `.buddhi/docs/`.
  - Added content hashing for incremental generation and staleness tracking.
  - Added `buddhi docs plan` command.
- Interactive Cytoscape.js code graph visualization (`tree-graph.html`).

### Changed
- Package renamed to `buddhi-ai` on PyPI.

## [1.0.0-beta.1] - [1.0.0-beta.4] - 2026-05-27

### Added
- Multi-language AST parsing using Tree-Sitter across Python, JavaScript, TypeScript, Go, Rust, C#, Java, Kotlin, Swift.
- SQLite code graph database generation (`tree-graph.db`) with recursive CTE query support.
- Cytoscape.js JSON export format (`tree-graph.json`).
- Topological community clustering using the Leiden algorithm.
- Initial CLI commands (`buddhi init`, `buddhi generate`).

