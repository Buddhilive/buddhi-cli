# Feature Specification: Pelican Static Site & Live Documentation with OKF v0.2 and Code Graph

**Feature Branch**: `009-pelican-static-site`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "I need to update and improve the `buddhi-cli` documentation implementation. Current documentation flow follows Google OKF v2.0. I want to implement Pelican Library to generate an static site as documentation where OKF will generate structured markdown files. A command like `buddhi docs` will run the live documentation site. The documentation process should use the current code graph as well (since it has been improved lately). First analyze the feasibility of implementing this live documentation, and if feasible, plan to implement it with `buddhi-cli`. Note: You can get inspiration from `graphify` project located in `./temp/graphify/` to see how they have implemented the documentation generation process."

---

## Executive Feasibility Analysis

### 1. Feasibility Verdict: **Feasible (High Confidence)**

Integrating the **Pelican** static site generator (`https://docs.getpelican.com/en/latest/index.html`) with **Google Open Knowledge Format (OKF)** (`https://github.com/GoogleCloudPlatform/open-knowledge-format`) and `buddhi-cli`'s Graphify-upgraded **SQLite Schema v2 Code Graph** (`.buddhi/graphs/tree-graph.db`) is architecturally sound, requires no external non-Python toolchains, and directly closes the gap between machine-readable OKF markdown bundles and human-browsable live documentation.

### 2. Key Technical Findings

1. **Programmatic Pelican Pipeline & Live Server (`pelican>=4.9`, `markdown>=3.4`)**:
   - Pelican exposes a native Python API (`pelican.Pelican`, `pelican.settings.read_settings`) and built-in HTTP serving (`pelican.server.RootedHTTPServer`, `ComplexHTTPRequestHandler`) alongside file-watching auto-reload.
   - `buddhi docs` (and `buddhi docs serve`) can orchestrate graph freshness checks, OKF markdown synthesis, Pelican static compilation (`.buddhi/site/`), and live HTTP serving (`http://127.0.0.1:61234`) within a single CLI command.
2. **Custom `OKFMarkdownReader` for OKF YAML Frontmatter**:
   - Standard Pelican `MarkdownReader` relies on `python-markdown`'s flat `Meta` extension (`Key: Value`), which cannot parse nested YAML objects or lists used by Google OKF (`sources: [{id, resource, content_hash}]`, `generated: {by, at}`, `relations: [{kind, target}]`, `verified: [...]`).
   - Subclassing `pelican.readers.BaseReader` into `OKFMarkdownReader` and reusing `buddhi.memory.frontmatter.split_frontmatter` (`yaml.safe_load`) allows Pelican to parse all OKF YAML frontmatter fields directly into Jinja2 `page.*` template variables while rendering Markdown bodies with `fenced_code`, `tables`, `toc`, and `codehilite`.
   - A Markdown link transformer rewrites portable relative `.md` links (`[Symbol](../symbols/mod.md)`) to `.html` URLs during Pelican HTML rendering while keeping the raw `.md` files on disk 100% agent-crawlable.
3. **Code Graph Intelligence Integration (Inspired by `graphify`)**:
   - `buddhi-cli`'s code graph (`src/buddhi/graph/`) was recently upgraded with `graphify`-inspired capabilities: Leiden community clustering with cohesion scores and hub naming (`clustering.py`), confidence tiers (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`), relationship contexts (`call`, `import`, `inherit`, `type_ref`), and topological analytics (`analyze.py`: `get_god_nodes`, `get_surprising_connections`, `suggest_questions`, `find_import_cycles`, `get_community_detail`, `get_graph_stats`).
   - However, `src/buddhi/docgen/planner.py` still only reads basic `CONTAINS`/`CALLS`/`INHERITS` edges and produces a flat `.buddhi/docs-plan.json` requiring an LLM pass (`/document-codebase`) before any `.buddhi/docs/` files exist.
   - By adapting patterns from `./temp/graphify/graphify/wiki.py` and `./temp/graphify/graphify/report.py`:
     - **Zero-LLM Instant Baseline**: `buddhi docs` deterministically generates an OKF v0.2 Architecture Report (`architecture-report.md`), Leiden Community articles (`communities/<slug>.md`), God Node deep-dive articles (`god-nodes/<slug>.md`), and structural symbol stub docs (`status: draft`) directly from `tree-graph.db` so the live site works immediately on any repository even before `/document-codebase` is run.
     - **Seamless LLM Enrichment**: When `/document-codebase` writes rich symbol prose (`status: stable`) with matching `sources[0].content_hash`, the generator preserves the LLM-authored prose while keeping community hubs, god-node pages, and cross-links synchronized.
     - **Two-Pass Slug & Link Resolution + Atomic Writes**: Adopting `graphify/wiki.py`'s Windows `MAX_PATH`-safe slugging, case-insensitive collision deduplication, `write_text_atomic_if_changed` (preventing infinite file-watcher loops), and end-of-run orphan cleanup ensures deterministic, cross-platform builds.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch Live Documentation Site via `buddhi docs` (Priority: P1)

As a developer or AI engineer working on a repository managed by `buddhi-cli`, I want to run `buddhi docs` (or `buddhi docs serve`) to automatically sync the code graph into structured OKF Markdown files, compile them with Pelican, and serve a live, hot-reloading documentation website locally so I can explore the codebase architecture, communities, god nodes, and symbol docs in my browser.

**Why this priority**: This delivers the core user-requested workflow (`buddhi docs` running the live documentation site backed by Pelican, OKF markdown, and the code graph) as a complete, standalone MVP slice.

**Independent Test**: Run `uv run buddhi docs --no-reload` or `uv run buddhi docs build` on a repository, verify that `.buddhi/docs/` is populated with valid OKF Markdown files and `.buddhi/site/index.html` (plus community, architecture report, and symbol HTML pages) is generated by Pelican and served over HTTP with exit code 0 and zero broken internal links.

**Acceptance Scenarios**:

1. **Given** an initialized repository with source code, **When** the user runs `buddhi docs` (or `buddhi docs serve --port 61234`), **Then** `buddhi` ensures `.buddhi/graphs/tree-graph.db` is current, generates/updates the OKF Markdown bundle under `.buddhi/docs/`, compiles the Pelican static site into `.buddhi/site/`, and starts a local HTTP server serving the documentation site at `http://127.0.0.1:61234` with live reload enabled by default.
2. **Given** OKF Markdown files under `.buddhi/docs/` containing nested YAML frontmatter (`type`, `title`, `description`, `status`, `tags`, `generated`, `sources`, `relations`), **When** Pelican compiles the site using `OKFMarkdownReader`, **Then** all YAML metadata is parsed without error and rendered in the page's provenance header/sidebar alongside the formatted Markdown body.
3. **Given** an edited OKF Markdown file in `.buddhi/docs/` while `buddhi docs` is running in live mode, **When** the file is saved, **Then** Pelican detects the change and incrementally rebuilds the affected HTML output without crashing or entering an infinite rebuild loop.

---

### User Story 2 - Graph-Grounded OKF Wiki, Architecture Report & Enriched Doc Planner (Priority: P2)

As a developer or coding agent, I want the OKF documentation generator and `buddhi docs plan` to incorporate the upgraded code graph intelligence (Leiden communities, cohesion scores, god nodes, surprising connections, import cycles, confidence tiers `EXTRACTED`/`INFERRED`/`AMBIGUOUS`, and review questions) inspired by `graphify`, so both agents reading `.buddhi/docs/` and humans browsing the Pelican site get topological insights alongside per-symbol docs.

**Why this priority**: Grounding documentation in the improved code graph transforms the site from a flat symbol list into an architectural knowledge base and ensures the site has rich content even before an LLM runs `/document-codebase`.

**Independent Test**: Run `uv run buddhi docs plan` and `uv run buddhi docs build`, then inspect `.buddhi/docs-plan.json`, `.buddhi/docs/index.md`, `.buddhi/docs/architecture-report.md`, `.buddhi/docs/communities/*.md`, and `.buddhi/docs/god-nodes/*.md` to verify they contain accurate graph metrics, OKF frontmatter, portable relative `.md` links, and preserved LLM symbol docs when `content_hash` matches.

**Acceptance Scenarios**:

1. **Given** a code graph in `.buddhi/graphs/tree-graph.db`, **When** `buddhi docs plan` or `buddhi docs build` runs, **Then** `.buddhi/docs-plan.json` includes enriched symbol metadata (`community_id`, `community_label`, `cohesion`, `is_god_node`, `degree`, `signature`, `edge_confidences`, and typed OKF `relations`).
2. **Given** a code graph with Leiden communities and topological analytics, **When** the OKF documentation bundle is synthesized, **Then** `buddhi` writes `.buddhi/docs/architecture-report.md` (corpus summary, confidence breakdown, git commit freshness, god nodes, surprising connections, import cycles, knowledge gaps, suggested questions), `.buddhi/docs/communities/<slug>.md` (one per community), and `.buddhi/docs/god-nodes/<slug>.md` (one per god node) with valid OKF YAML frontmatter.
3. **Given** existing LLM-authored symbol documentation in `.buddhi/docs/` whose `sources[0].content_hash` matches the current AST snippet hash, **When** `buddhi docs build` or `buddhi docs` runs, **Then** the existing prose and `status: stable` frontmatter are preserved untouched, whereas undocumented symbols receive deterministic structural OKF docs (`status: draft`) so no internal links are broken.

---

### User Story 3 - Accessible, Anti-Slop Documentation Theme, Search & Interactive Graph View (Priority: P3)

As a human reader browsing the generated Pelican documentation site, I want an accessible (WCAG 2.2 AA), responsive, zero-slop documentation interface with client-side symbol/concept search, Mermaid architecture diagrams, OKF provenance badges, and navigation to the interactive code graph (`tree-graph.html`) so I can quickly locate symbols and verify documentation freshness.

**Why this priority**: A static site is only as effective as its navigation, readability, accessibility, and search experience.

**Independent Test**: Build the site with `uv run buddhi docs build`, run `uv run buddhi scripts verify-a11y` and `uv run buddhi scripts contrast` against the bundled theme templates/CSS, verify client-side search index (`search-index.json`) generation, and confirm every navigation link resolves to an existing HTML page.

**Acceptance Scenarios**:

1. **Given** a compiled Pelican site in `.buddhi/site/`, **When** inspected in a browser or audited with `buddhi scripts verify-a11y` and `buddhi scripts contrast`, **Then** all pages use semantic HTML5 landmarks, keyboard-operable navigation and search with visible `:focus-visible` indicators, light/dark theme parity with >= 4.5:1 normal text contrast, and zero dead links or forbidden AI-slop patterns.
2. **Given** the generated static site, **When** the user types a symbol name, community label, or tag into the search bar, **Then** the client-side search filters `.buddhi/site/search-index.json` and navigates directly to the matching page.
3. **Given** `.buddhi/graphs/tree-graph.html` generated by `buddhi`, **When** the Pelican site builds, **Then** the interactive graph visualization is copied/linked into the static site navigation so users can switch between OKF prose and interactive graph exploration.

---

### Edge Cases

- **Windows `MAX_PATH` & Case-Insensitive Collisions**: Community names, qualified symbol names (e.g., deeply nested classes/functions), or god-node labels that differ only by casing (`Parser` vs `parser`) or contain Windows-reserved characters (`<>:"/\|?*#%()`) MUST be sanitized via two-pass slug resolution with a Windows `MAX_PATH` length budget and case-folded collision suffixes (`_2`, `_3`) so builds never fail with `FileNotFoundError` or overwrite files on NTFS/APFS.
- **Infinite File-Watcher Rebuild Loops**: Writing unchanged `.md` files during a rebuild updates file `mtime` and triggers file watchers again. All generated OKF `.md` files MUST use content-hash / byte-comparison atomic writes (`write_text_atomic_if_changed`) so unchanged files never touch disk timestamps.
- **Orphaned Community / God-Node Pages**: When code changes cause a Leiden community label to shift or a symbol to no longer rank as a god node, stale generated community/god-node `.md` files MUST be swept at the end of the run using a manifest or directory scope without deleting user-authored or valid per-symbol OKF docs.
- **Forbidden OKF Attested Computation Fields**: Consistent with `.agents/rules/okf-docs.md` and `src/buddhi/memory/frontmatter.py`, `OKFMarkdownReader` and the OKF generator MUST strip/forbid OKF Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`).
- **Port Conflicts on Live Server**: If the default port (`61234`) is already in use when running `buddhi docs`, the CLI MUST either report a clear actionable error suggesting `--port <PORT>` or bind to the user-specified `--port` cleanly without an unhandled traceback.
- **Empty or Uninitialized Repository**: If `.buddhi/graphs/tree-graph.db` does not exist when `buddhi docs` is invoked, `buddhi` MUST automatically run the graph generation pipeline first (unless `--no-graph-refresh` is passed) and handle zero-symbol repositories gracefully by rendering an empty-state index page.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Pelican Dependency & Packaging)**: `pyproject.toml` MUST include `pelican[markdown]>=4.9.0` (or `pelican>=4.9.0` and `markdown>=3.4.0`) in project dependencies so `buddhi docs` works out of the box on Python >= 3.10.
- **FR-002 (`buddhi docs` CLI Command Group)**: `src/buddhi/commands/docs.py` MUST expose:
  - `buddhi docs` (default callback when invoked without a subcommand) and `buddhi docs serve`: refreshes graph & OKF docs, builds the Pelican site into `.buddhi/site/` (or `--output`), and serves it locally (`--host 127.0.0.1`, `--port 61234`, `--open / --no-open`, `--reload / --no-reload`).
  - `buddhi docs build`: refreshes graph & OKF docs and compiles the static HTML site into `.buddhi/site/` (or `--output`) without starting an HTTP server.
  - `buddhi docs plan`: preserves backward-compatible `.buddhi/docs-plan.json` generation while enriching entries with code graph topology metadata.
- **FR-003 (Custom `OKFMarkdownReader`)**: `buddhi` MUST provide a Pelican reader subclass (`OKFMarkdownReader`) that parses OKF YAML frontmatter (`--- ... ---`) via `yaml.safe_load` (`split_frontmatter`), strips forbidden Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`), maps OKF fields (`type`/`kind`, `title`, `description`/`summary`, `status`, `confidence`, `tags`, `generated`, `verified`, `sources`, `relations`) onto Pelican `Page` metadata, and rewrites relative `.md` links to `.html` links in rendered HTML.
- **FR-004 (Code Graph Topology Integration)**: The documentation generator (`src/buddhi/docgen/`) MUST query `.buddhi/graphs/tree-graph.db` (Schema v2) using `src/buddhi/graph/analyze.py` and `src/buddhi/graph/model.py` to generate:
  - `.buddhi/docs/index.md` (OKF bundle root with `okf_version: "0.2"`, graph summary, community catalog, god-node catalog, and module index).
  - `.buddhi/docs/architecture-report.md` (Graphify-inspired structural report: corpus stats, confidence breakdown `EXTRACTED`/`INFERRED`/`AMBIGUOUS`, git `built_at_commit` freshness, god nodes, surprising cross-community connections, import cycles, knowledge gaps, and suggested review questions).
  - `.buddhi/docs/communities/<slug>.md` (one OKF doc per Leiden community with cohesion score, hub node, degree-ranked members, cross-community links, source files, confidence audit trail, and Mermaid relationship diagram).
  - `.buddhi/docs/god-nodes/<slug>.md` (one OKF doc per god node with degree, community link, and connections grouped by relation kind and confidence tier).
- **FR-005 (Incremental Symbol Docs & Content-Hash Preservation)**: For every symbol in `build_docs_plan`, if an existing OKF doc at `doc_path` has a matching `sources[0].content_hash` and `status: stable`, the generator MUST preserve its prose. If no doc exists yet, `buddhi docs build` / `serve` MUST generate a deterministic structural OKF doc (`status: draft`, containing signature, file/line source anchor, community link, and caller/callee links) so every symbol link on the site resolves.
- **FR-006 (Two-Pass Slug Resolution, Atomic Writes & Orphan Sweeping)**: All generated OKF docs MUST use a two-pass slug resolver (Windows `MAX_PATH`-aware, case-insensitive collision deduplication), `write_text_atomic_if_changed` (writing to disk only when content bytes change), and end-of-run orphan cleanup for stale community/god-node files.
- **FR-007 (Client-Side Search & Interactive Graph Integration)**: `buddhi docs build` MUST emit a lightweight JSON search index (`.buddhi/site/search-index.json`) covering all pages (titles, kinds, summaries, tags, file paths, URLs) and copy/link `.buddhi/graphs/tree-graph.html` into `.buddhi/site/graphs/tree-graph.html`.
- **FR-008 (Accessibility & Anti-Slop Compliance)**: The bundled Pelican theme (`src/buddhi/docgen/theme/`) MUST comply with the workspace `a11y` skill (WCAG 2.2 AA / Standard profile: semantic HTML landmarks, keyboard navigation, `:focus-visible` focus rings, >= 4.5:1 normal text contrast in both light and dark themes, empty/loading/error states for search) and `antislop` rules (purposeful technical typography and palette, zero dead links, zero fabricated claims, no em-dashes in UI copy).
- **FR-009 (Harness Skill & Ignore Updates)**: `.buddhi/.gitignore` creation in `src/buddhi/util/fsutil.py` MUST ignore `site/` alongside `graphs/` and `docs/`, and `.agents/skills/document-codebase/SKILL.md` and `.agents/skills/repoagent-doc-generation/SKILL.md` MUST be updated to reference the enriched OKF schema and `buddhi docs build` / `buddhi docs` workflow.
- **FR-010 (Project Documentation & Attribution)**: `CHANGELOG.md` (under `[Unreleased]`), `ACKNOWLEDGMENTS.md` (referencing Pelican, Google Open Knowledge Format, and Graphify), and `README.md` MUST be updated to document the new Pelican + OKF + Code Graph live documentation architecture and CLI commands.

### Key Entities

- **`OKFDocNode`**: Represents a single Open Knowledge Format v0.2 Markdown document on disk (`.buddhi/docs/**/*.md`) with structured YAML frontmatter (`type`, `title`, `description`, `status`, `confidence`, `tags`, `generated`, `sources`, `relations`) and Markdown body.
- **`PlanEntry` (Enriched)**: Represents a topologically ordered symbol in `.buddhi/docs-plan.json`, extended with `community_id`, `community_label`, `cohesion`, `is_god_node`, `degree`, `signature`, `edge_confidences`, and `relations`.
- **`OKFMarkdownReader`**: Custom Pelican `BaseReader` adapter that parses OKF YAML frontmatter, validates/strips forbidden fields, transforms relative `.md` links to `.html`, and feeds `Page` objects to Pelican's Jinja2 theme templates.
- **`DocsSiteConfig`**: Configuration model holding workspace root, `.buddhi/docs` content path, `.buddhi/site` output path, host, port, autoreload toggle, and theme settings passed programmatically to `pelican.settings.read_settings`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Zero-Config Live Site Execution)**: Running `buddhi docs build` on `buddhi-cli` itself completes in under 10 seconds with exit code 0, producing `.buddhi/site/index.html`, `architecture-report.html`, community pages, god-node pages, symbol pages, and `search-index.json`.
- **SC-002 (100% Internal Link Integrity)**: Every internal link emitted across generated HTML pages (index -> communities, communities -> god nodes/symbols, symbols -> callers/callees) resolves to an existing generated HTML file (0 broken links).
- **SC-003 (Idempotent Incremental Rebuilds)**: Running the OKF doc synthesis pass twice in a row without source code changes results in 0 file writes on the second pass (`write_text_atomic_if_changed`), preventing file-watcher feedback loops.
- **SC-004 (Accessibility & Contrast Gate Pass)**: Running `buddhi scripts verify-a11y` and `buddhi scripts contrast` on the bundled Pelican theme templates and stylesheet exits with code 0 (WCAG 2.2 AA compliance across both light and dark modes).
- **SC-005 (Test, Lint & Typecheck Verification)**: `uv run pytest`, `uv run ruff check .`, and `uv run mypy src/ tests/` pass with exit code 0.

---

## Assumptions

- **OKF Version Alignment**: The user prompt mentions "Google OKF v2.0", which refers to the **Google Open Knowledge Format** (`https://github.com/GoogleCloudPlatform/open-knowledge-format`, currently versioned `0.2` in the official repository and in `buddhi-cli`'s `okf_version: "0.2"` headers, alongside `tree-graph.db` Schema v2). The implementation will support `okf_version: "0.2"` (and accept `"2.0"` as a valid alias in `OKFMarkdownReader` for forward/user compatibility).
- **No LLM API Calls Inside `buddhi` CLI**: Consistent with `buddhi-cli`'s core architecture principle ("buddhi never calls an LLM itself"), `buddhi docs` deterministically generates graph-grounded structural OKF docs (`status: draft`), community articles, god-node pages, and the architecture report in pure Python, while `/document-codebase` (run by the Antigravity agent) authors rich semantic prose (`status: stable`) that Pelican renders seamlessly.
- **Localhost Binding by Default**: `buddhi docs` binds the live HTTP server to `127.0.0.1:61234` by default for local security, with `--host` and `--port` flags for customization.
