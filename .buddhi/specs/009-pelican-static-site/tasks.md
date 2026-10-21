# Tasks: Pelican Static Site & Live Documentation with OKF v0.2 and Code Graph

**Feature Branch**: `009-pelican-static-site`

**Input**: Design documents from `.buddhi/specs/009-pelican-static-site/` (`spec.md`, `plan.md`)

**Prerequisites**: `spec.md` (complete), `plan.md` (complete)

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Every task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure & Dependencies)

**Purpose**: Configure dependencies and project layout for Pelican, OKF v0.2, and code graph documentation.

- [x] T001 Update `pyproject.toml` to add `pelican>=4.9.0` and `markdown>=3.4.0` to project dependencies, and `types-markdown` to dev dependency group.
- [x] T002 Update `src/buddhi/util/fsutil.py` to add `site/` to `.buddhi/.gitignore` alongside `graphs/` and `docs/` in `ensure_buddhi_dirs`.
- [x] T003 [P] Create initial directory scaffold for documentation engine: `src/buddhi/docgen/theme/templates/partials/`, `src/buddhi/docgen/theme/static/css/`, `src/buddhi/docgen/theme/static/js/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and cross-platform safe slugging needed before doc generation and site compilation.

**CRITICAL**: Foundational tasks must complete before user story pipelines begin.

- [x] T004 Implement `src/buddhi/docgen/slug.py` providing `stem_filename_budget` (Windows `MAX_PATH` protection), `_safe_filename` (sanitizing reserved characters while preserving dunder names), two-pass slug resolver with case-insensitive collision suffixes (`_2`, `_3`), and `write_text_atomic_if_changed` (byte comparison atomic writes preventing infinite file-watcher loops).
- [x] T005 [P] Create `src/buddhi/docgen/__init__.py` exporting public entrypoints (`build_docs_plan`, `generate_docs_bundle`, `OKFMarkdownReader`, `compile_site`, `serve_docs`).

**Checkpoint**: Foundation ready: safe slugging, atomic file writers, and module entrypoints established.

---

## Phase 3: User Story 1 - Launch Live Documentation Site via `buddhi docs` (Priority: P1) 🎯 MVP

**Goal**: Implement the custom Pelican reader (`OKFMarkdownReader`), the programmatic site compiler & live server orchestrator (`site.py`), and the refactored CLI command group in `src/buddhi/commands/docs.py` to compile and serve live docs at `http://127.0.0.1:8000`.

**Independent Test**: Running `uv run buddhi docs build` compiles `.buddhi/docs/` into `.buddhi/site/` with zero errors, and running `uv run buddhi docs --no-reload` starts the live HTTP server responding with HTTP 200 on `http://127.0.0.1:8000/index.html`.

### Tests for User Story 1
- [x] T006 [P] [US1] Write unit tests in `tests/test_docgen_reader.py` validating `OKFMarkdownReader`: nested OKF YAML frontmatter parsing (`sources`, `relations`, `generated`), stripping forbidden Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`), Markdown body conversion, and relative `.md` link rewriting to `.html`.
- [x] T007 [P] [US1] Write CLI and server tests in `tests/test_commands_docs.py` validating `buddhi docs build`, `buddhi docs serve`, ephemeral port binding, HTTP GET 200 response, and clean socket shutdown.

### Implementation for User Story 1
- [x] T008 [US1] Implement `src/buddhi/docgen/reader.py` (`OKFMarkdownReader` subclassing `pelican.readers.BaseReader`) using `split_frontmatter` (`yaml.safe_load`), stripping forbidden fields, mapping metadata to Pelican `Page`, rendering markdown with extensions, and regex-rewriting relative `.md` links to `.html`.
- [x] T009 [US1] Implement `src/buddhi/docgen/site.py` providing `get_pelican_settings`, `compile_site` (running `Pelican(settings).run()`), pre-bind socket conflict check, and `serve_docs` (running `RootedHTTPServer` with background file watcher).
- [x] T010 [US1] Refactor `src/buddhi/commands/docs.py` with Typer `invoke_without_command=True`: default callback runs live documentation (`buddhi docs`), and add subcommands `serve`, `build`, and `plan`.

**Checkpoint**: User Story 1 is functional: `buddhi docs` compiles OKF markdown and serves a live static documentation site.

---

## Phase 4: User Story 2 - Graph-Grounded OKF Wiki, Architecture Report & Enriched Doc Planner (Priority: P2)

**Goal**: Query the upgraded Schema v2 code graph (`tree-graph.db`) via `src/buddhi/graph/analyze.py` to synthesize `architecture-report.md`, community hubs (`communities/<slug>.md`), god-node deep dives (`god-nodes/<slug>.md`), and structural symbol stubs while preserving LLM-authored symbol prose (`status: stable`) when `content_hash` matches.

**Independent Test**: Running `uv run buddhi docs plan` outputs enriched topological metadata in `.buddhi/docs-plan.json`, and running `uv run buddhi docs build` generates valid OKF markdown articles under `.buddhi/docs/` with accurate Leiden community metrics, god nodes, and 0 broken cross-links.

### Tests for User Story 2
- [x] T011 [P] [US2] Write generator and slug tests in `tests/test_docgen_generator.py`: SQLite fixture with 2 communities and 1 god node, verifying generation of `index.md`, `architecture-report.md`, `communities/<slug>.md`, `god-nodes/<slug>.md`, and structural symbol stubs.
- [x] T012 [P] [US2] Add incremental hash tests in `tests/test_docgen_generator.py` asserting existing LLM symbol docs with matching `sources[0].content_hash` are preserved untouched, while changed snippets are flagged for update.
- [x] T013 [P] [US2] Add atomic write and orphan sweeping tests in `tests/test_docgen_generator.py` asserting 0 file writes when rerun without changes (`SC-003`) and verifying stale community/god-node files are unlinked without touching symbol docs.

### Implementation for User Story 2
- [x] T014 [US2] Enrich `src/buddhi/docgen/planner.py` (`PlanEntry`) to include topological attributes from the code graph: `community_id`, `community_label`, `cohesion`, `is_god_node`, `degree`, `signature`, `edge_confidences`, and typed OKF `relations`.
- [x] T015 [US2] Implement `src/buddhi/docgen/generator.py`:
  - Query `.buddhi/graphs/tree-graph.db` using `src/buddhi/graph/analyze.py` (`get_graph_stats`, `get_god_nodes`, `get_surprising_connections`, `suggest_questions`, `find_import_cycles`, `get_community_detail`).
  - Synthesize `.buddhi/docs/index.md` (OKF bundle root with `okf_version: "0.2"`).
  - Synthesize `.buddhi/docs/architecture-report.md` (corpus metrics, confidence breakdown, commit freshness, god nodes, import cycles, knowledge gaps, suggested questions).
  - Synthesize `.buddhi/docs/communities/<slug>.md` with Leiden cohesion score, degree-ranked members, cross-community links, and Mermaid `flowchart LR` diagram.
  - Synthesize `.buddhi/docs/god-nodes/<slug>.md` grouping connections by relation kind and confidence tier.
  - Synthesize structural symbol stubs (`status: draft`) for undocumented symbols, preserving existing LLM prose when `sources[0].content_hash` matches.
  - Execute end-of-run orphan sweeper on obsolete generated community and god-node files.
- [x] T016 [US2] Wire `src/buddhi/docgen/generator.py` into `compile_site` in `src/buddhi/docgen/site.py` and `buddhi docs build` / `buddhi docs serve` in `src/buddhi/commands/docs.py`.

**Checkpoint**: User Story 2 complete: code graph topology is automatically turned into structured OKF documentation with zero broken links.

---

## Phase 5: User Story 3 - Accessible, Anti-Slop Documentation Theme, Search & Interactive Graph View (Priority: P3)

**Goal**: Deliver a WCAG 2.2 AA compliant, developer-focused Pelican documentation theme (`src/buddhi/docgen/theme/`) with light/dark theme parity, client-side search (`search-index.json` + `search.js`), and navigation to the interactive Cytoscape graph (`tree-graph.html`).

**Independent Test**: Running `uv run buddhi scripts verify-a11y . --src src/buddhi/docgen/theme/` and `uv run buddhi scripts contrast --css src/buddhi/docgen/theme/static/css/theme.css` passes with exit code 0, client-side search functions via keyboard (`/`, `ArrowUp`/`ArrowDown`, `Enter`, `Esc`), and clicking the interactive graph button opens `tree-graph.html`.

### Tests for User Story 3
- [x] T017 [P] [US3] Add automated theme accessibility and contrast verification tests in `tests/test_commands_docs.py` invoking `buddhi scripts verify-a11y` and `buddhi scripts contrast` against `src/buddhi/docgen/theme/`.
- [x] T018 [P] [US3] Add link integrity crawler test in `tests/test_commands_docs.py` crawling all generated HTML files in `.buddhi/site/` to verify 100% of internal links resolve to valid destinations (`SC-002`).

### Implementation for User Story 3
- [x] T019 [US3] Implement semantic HTML5 templates in `src/buddhi/docgen/theme/templates/`:
  - `base.html`: HTML5 landmarks, skip-to-content link, search dialog markup, header actions, and footer.
  - `page.html`: Concept doc layout, breadcrumbs, TOC right-rail, OKF provenance badge strip, and source code anchors.
  - `index.html`: Portal home with corpus summary card, community grid, god-node list, and quick navigation.
  - `partials/nav_sidebar.html`: Hierarchical sidebar with `aria-current="page"` and section groupings.
  - `partials/breadcrumbs.html`: Accessible breadcrumb trail.
  - `partials/provenance.html`: OKF v0.2 metadata badges (`okf_type`, `status`, `confidence`, `sources`, `relations`).
  - `partials/toc.html`: In-page table of contents.
- [x] T020 [US3] Implement accessible CSS stylesheet in `src/buddhi/docgen/theme/static/css/theme.css`:
  - CSS custom properties for light and dark themes.
  - Verified text contrast >= 4.5:1 (light: 17.85:1, dark: 17.48:1) and UI borders >= 3.0:1 (light: 4.76:1, dark: 4.02:1).
  - Universal `:focus-visible` indicators (`outline: 2px solid var(--color-focus-ring); outline-offset: 2px`).
  - Responsive mobile reflow down to 320px viewport without horizontal overflow.
- [x] T021 [US3] Implement client-side search UI in `src/buddhi/docgen/theme/static/js/search.js`:
  - WAI-ARIA combobox with `aria-activedescendant` and live screen reader status updates.
  - Keyboard shortcuts (`/` or `Ctrl+K` to open, `ArrowUp`/`ArrowDown` to navigate, `Enter` to open, `Esc` to close).
  - Three distinct UI states: Loading, Empty ("No results found"), and Error.
- [x] T022 [US3] Implement `theme-toggle.js` in `src/buddhi/docgen/theme/static/js/theme-toggle.js` supporting `prefers-color-scheme` and persistent theme preference in `localStorage`.
- [x] T023 [US3] Generate client-side search index (`.buddhi/site/search-index.json`) and copy/link `.buddhi/graphs/tree-graph.html` into `.buddhi/site/graphs/tree-graph.html` in `src/buddhi/docgen/site.py`.

**Checkpoint**: User Story 3 complete: accessible documentation theme, hotkey search, and interactive graph navigation verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Agent harness skills integration, full test suite execution, and documentation alignment.

- [x] T024 [P] Update `.agents/skills/document-codebase/SKILL.md` and `.agents/skills/repoagent-doc-generation/SKILL.md` to reference the enriched OKF schema, `buddhi docs build`, and `buddhi docs` live workflow.
- [x] T025 [P] Update `.agents/memory/MEMORY.md` (or add OKF concept note via `buddhi memory add`) recording the decision to use Pelican static site generator and OKF v0.2 custom reader.
- [x] T026 Execute full verification gate via `terminal-runner`:
  - `uv run pytest` (all unit, integration, and E2E tests pass)
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src/ tests/`
  - `uv run buddhi docs build` (verify completion in < 10 seconds, `SC-001`)

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Can start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 completion. Blocks all User Stories.
- **Phase 3 (User Story 1 - P1 MVP)**: Depends on Phase 2 completion. Delivers working live documentation server.
- **Phase 4 (User Story 2 - P2)**: Depends on Phase 3 completion. Enriches OKF markdown with code graph topology.
- **Phase 5 (User Story 3 - P3)**: Depends on Phase 3 completion (can run in parallel with Phase 4 on theme templates).
- **Phase 6 (Polish)**: Depends on Phases 3, 4, and 5 completion.

### Parallel Opportunities
- T001, T002, T003 can run in parallel during Setup.
- T006 and T007 (US1 tests) can run in parallel before US1 implementation.
- T011, T012, T013 (US2 tests) can run in parallel.
- T017, T018 (US3 tests) can run in parallel.
- T019 (templates), T020 (CSS), T021 (search JS) touch different files and can be authored in parallel.

