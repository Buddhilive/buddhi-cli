# Implementation Plan: Pelican Static Site & Live Documentation with OKF v0.2 and Code Graph

**Branch**: `009-pelican-static-site` | **Date**: 2026-10-27 | **Spec**: [.buddhi/specs/009-pelican-static-site/spec.md](spec.md)

**Input**: Feature specification from `.buddhi/specs/009-pelican-static-site/spec.md`

---

## Summary

This feature updates and improves the `buddhi-cli` documentation implementation by synthesizing the **Google Open Knowledge Format (OKF v0.2)**, the **Pelican** static site generator (`https://docs.getpelican.com/en/latest/index.html`), and `buddhi-cli`'s Schema v2 **Code Graph** (inspired by `graphify`'s `wiki.py` and `report.py`).

Running `buddhi docs` (or `buddhi docs serve`) ensures the code graph is up to date, extracts topological intelligence from `.buddhi/graphs/tree-graph.db` (Leiden communities, cohesion scores, god nodes, confidence tiers, and surprising connections), synthesizes an agent-crawlable OKF Markdown bundle under `.buddhi/docs/`, and compiles it into an accessible (WCAG 2.2 AA), light/dark static documentation site in `.buddhi/site/` served live on `http://127.0.0.1:8000` with hot reloading. A custom `OKFMarkdownReader` bridges OKF YAML frontmatter into Pelican templates while rewriting `.md` links to `.html` in rendered pages. Existing LLM-authored symbol prose (`status: stable`) is preserved when snippet hashes match, and zero-LLM deterministic structural stubs (`status: draft`) ensure 100% link integrity across the site.

---

## Technical Context

**Language/Version**: Python >= 3.10 (tested on Python 3.10, 3.11, 3.12, 3.13)

**Primary Dependencies**:
- `pelican>=4.9.0`: Programmatic static site generator and live HTTP server
- `markdown>=3.4.0`: Python Markdown parser with `fenced_code`, `tables`, `toc`, and `codehilite` extensions
- `pyyaml>=6.0`: Safe YAML frontmatter parsing and serialization
- `typer>=0.27.1`: CLI interface and command group
- `igraph>=1.0.0` & `tree-sitter>=0.26.0`: Code graph engine and AST parsing

**Storage**:
- SQLite Schema v2: `.buddhi/graphs/tree-graph.db` (`nodes`, `edges`, `communities`, `extract_cache`, `meta`)
- Filesystem: `.buddhi/docs/` (structured OKF Markdown files), `.buddhi/site/` (compiled static HTML/CSS/JS site)

**Testing**:
- `pytest>=9.1.1`: Unit, integration, CLI, and end-to-end site crawler tests
- `buddhi scripts verify-a11y`: Static accessibility gate on theme templates
- `buddhi scripts contrast`: WCAG 2.2 AA contrast calculation on theme color tokens and stylesheets

**Target Platform**: Cross-platform (Windows, macOS, Linux). Strict adherence to Windows `MAX_PATH` length constraints and case-insensitive filename collision handling.

**Project Type**: CLI tool & developer documentation generator

**Performance Goals**:
- Full static site compilation (`buddhi docs build`) completes in under 10 seconds for standard repositories (~1,000 symbols)
- Zero file writes and zero watcher triggers on unchanged rebuilds (`write_text_atomic_if_changed`)
- Sub-50ms search query response via client-side `search-index.json`

**Constraints**:
- Pure Python implementation (no Node.js, Ruby, or external binary dependencies)
- 100% link integrity: zero dead links across generated HTML pages
- Non-destructive: LLM-authored symbol docs are never overwritten when `sources[0].content_hash` matches
- Security: Forbidden OKF Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`) are stripped

---

## AGENTS.md Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Project build & test commands adhered to**:
  - Install: `uv sync`
  - Build: `uv build`
  - Test: `uv run pytest`
  - Lint & Format: `uv run ruff check .` / `uv run ruff format --check .`
  - Typecheck: `uv run mypy src/ tests/`
- [x] **Architectural constraints respected**:
  - Generated codebase documentation lives under `.buddhi/docs/` as OKF Markdown
  - `sources[0].content_hash` verified for staleness detection
  - Attested Computation fields stripped from documentation nodes
  - File modifications use atomic write patterns (`write_text_atomic_if_changed`)
- [x] **No unapproved external dependencies introduced**:
  - `pelican` and `markdown` are standard Python libraries compatible with project license and PyPI release

---

## System Design & Architectural Lenses Evaluation

### 1. Architectural Decisions & Alternatives Considered

| Decision Area | Selected Approach | Alternative Considered | Rationale for Selection |
| :--- | :--- | :--- | :--- |
| **Static Site Generator** | **Pelican** (`pelican.Pelican` API) | MkDocs, Sphinx, custom script | Requested by user. Pelican provides a clean Python API, built-in live server with autoreload, flexible Jinja2 templating, and custom reader extensibility without external toolchains. |
| **Frontmatter Parsing** | Custom **`OKFMarkdownReader`** subclassing `pelican.readers.BaseReader` | `python-markdown` `meta` extension | Standard `meta` extension only supports flat `Key: Value` strings and fails on nested YAML structures in OKF v0.2 (`sources: [...]`, `relations: [...]`, `generated: {...}`). `OKFMarkdownReader` uses `split_frontmatter` (`yaml.safe_load`) cleanly. |
| **Link Integrity** | **Dual-format links**: `.md` on disk, rewritten to `.html` in rendered output | Raw `[[wikilinks]]` or hardcoded `.html` in markdown | Keeps `.buddhi/docs/` markdown files 100% crawlable on disk by AI agents and editors, while allowing browser users to navigate rendered HTML without 404s. |
| **Documentation Baseline** | **Deterministic Graph Synthesis + LLM Enrichment** | LLM-only doc generation | Allows `buddhi docs` to serve an immediate, useful architectural site on any repo even before `/document-codebase` is run, while seamlessly preserving rich LLM prose when available. |
| **File I/O & Watchers** | **`write_text_atomic_if_changed`** | Direct `path.write_text` | Direct file writes change file `mtime` even when content is identical, causing infinite rebuild loops in Pelican's file watcher. Byte-comparison atomic replace prevents churn. |

### 2. Multi-Angle Perspectives

- **Fewest-Slices Lens**:
  - *Slice 1 (Core Reader & Site Engine)*: `OKFMarkdownReader` and `site.py` compile existing `.buddhi/docs/` into `.buddhi/site/`.
  - *Slice 2 (Graph-to-OKF Synthesis Pipeline)*: `generator.py` extracts topology from `tree-graph.db` and emits `architecture-report.md`, `communities/`, `god-nodes/`, and structural stubs.
  - *Slice 3 (CLI Commands & Live Server)*: `commands/docs.py` wires `buddhi docs` (live serve), `build`, `serve`, and `plan`.
  - *Slice 4 (Accessible Theme, Search & Interactive Graph)*: Bundled Jinja2 templates, accessible CSS, client-side search, and Cytoscape viewer link.
- **Risk-First Lens**:
  - *Windows `MAX_PATH` & Case Collisions*: Solved by `stem_filename_budget` and case-insensitive suffix collision handling (`used_slugs`).
  - *Watcher Loops*: Solved by `write_text_atomic_if_changed`.
  - *Port Collisions*: Pre-bind socket probing displays actionable guidance (`Port in use, run with --port <PORT>`).
  - *Stale Community Files*: End-of-run orphan sweeper cleans obsolete generated files without touching user docs.
- **Seam-Quality Lens**:
  - Clean separation between Code Graph analysis (`graph/analyze.py`), OKF Markdown synthesis (`docgen/generator.py`), Pelican site compilation (`docgen/site.py`), and CLI invocation (`commands/docs.py`).

---

## Project Structure

### Documentation (this feature)

```text
.buddhi/specs/009-pelican-static-site/
├── spec.md              # Feature specification
├── plan.md              # This file (/spec-plan command output)
└── tasks.md             # Implementation tasks (/spec-tasks command output)
```

### Source Code (repository root)

```text
src/buddhi/
├── commands/
│   ├── docs.py                 # REFACTORED: Typer group (default invoke, serve, build, plan)
│   └── ...
├── docgen/
│   ├── __init__.py             # Public docgen API exports
│   ├── planner.py              # ENRICHED: PlanEntry with topology metadata
│   ├── slug.py                 # NEW: Safe slugging, Windows MAX_PATH budgeting, collision dedup
│   ├── generator.py            # NEW: Graph-to-OKF synthesis pipeline (reports, communities, god-nodes, stubs)
│   ├── reader.py               # NEW: Custom Pelican OKFMarkdownReader
│   ├── site.py                 # NEW: Pelican orchestrator (settings builder, compile_site, search index, live server)
│   └── theme/                  # NEW: Bundled WCAG 2.2 AA accessible Pelican theme
│       ├── templates/
│       │   ├── base.html       # HTML5 landmarks, skip link, search modal
│       │   ├── page.html       # OKF concept doc view, provenance sidebar, TOC
│       │   ├── index.html      # Portal homepage, corpus summary, quick links
│       │   └── partials/
│       │       ├── nav_sidebar.html
│       │       ├── breadcrumbs.html
│       │       ├── provenance.html
│       │       └── toc.html
│       └── static/
│           ├── css/
│           │   └── theme.css   # Semantic CSS custom properties, light/dark contrast verified
│           └── js/
│               ├── search.js   # Client-side combobox search
│               └── theme-toggle.js
└── util/
    └── fsutil.py               # UPDATED: ignore site/ alongside graphs/ and docs/ in .buddhi/.gitignore

tests/
├── test_docgen_reader.py       # NEW: OKFMarkdownReader unit tests
├── test_docgen_generator.py    # NEW: Synthesis pipeline, slugs, atomic writes, orphan sweeping tests
└── test_commands_docs.py       # NEW: CLI build, serve, plan, and link integrity crawler tests
```

---

## Subsystem Specifications

### 1. Custom Pelican Reader (`src/buddhi/docgen/reader.py`)

- **Class**: `OKFMarkdownReader(BaseReader)`
- **File Extensions**: `["md", "markdown"]`
- **Frontmatter Processing**:
  - Uses `buddhi.memory.frontmatter.split_frontmatter(text)` to extract YAML dictionary and Markdown body.
  - Automatically strips forbidden Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`).
  - Normalizes keys to lowercase: `title`, `summary`, `status`, `kind`, `okf_version`, `sources`, `relations`, `generated`, `tags`, `community_id`, `cohesion`.
  - Determines hierarchical URL and output path relative to content directory (`save_as = rel_path.with_suffix(".html")`, `url = save_as`).
- **Markdown Conversion**:
  - Converts body with extensions: `fenced_code`, `tables`, `toc`, `codehilite`.
- **Link Rewriting**:
  - Regular expression replaces relative markdown targets (`<a href="...path/file.md#anchor">`) with `<a href="...path/file.html#anchor">`.
  - External (`http://`, `https://`, `mailto:`) and non-markdown links (`tree-graph.html`) remain unchanged.

### 2. Graph-to-OKF Synthesis Pipeline (`src/buddhi/docgen/generator.py` & `slug.py`)

- **Topology Queries**:
  - Connects to `.buddhi/graphs/tree-graph.db` using `src/buddhi/graph/analyze.py` (`get_graph_stats`, `get_god_nodes`, `get_surprising_connections`, `suggest_questions`, `find_import_cycles`, `get_community_detail`).
- **Generated Markdown Articles**:
  - `.buddhi/docs/index.md`: Portal index cataloging communities, god nodes, modules, and architecture report.
  - `.buddhi/docs/architecture-report.md`: Graph audit report with corpus size, confidence breakdown (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`), commit freshness, god nodes, import cycles, knowledge gaps, and suggested review questions.
  - `.buddhi/docs/communities/<slug>.md`: Community hub with cohesion rating, key member symbols ranked by degree, cross-community links, audit trail, and Mermaid `flowchart LR` diagram.
  - `.buddhi/docs/god-nodes/<slug>.md`: Core abstraction article with community backlink and incident connections grouped by relation and confidence tier.
  - Structural Symbol Stubs: For every node in `build_docs_plan`:
    - If doc exists with `status: stable` and matching `content_hash`: preserved untouched.
    - If doc missing or snippet hash changed: generates structural OKF doc (`status: draft`) with signature, source code lines, and caller/callee links.
- **Two-Pass Safe Slug Resolution (`slug.py`)**:
  - `stem_filename_budget(output_dir, reserve=5, limit=200)` enforces Windows `MAX_PATH` budget.
  - `_safe_filename(name, limit)` sanitizes reserved characters while preserving dunder names.
  - Pass 1 builds label -> unique slug dictionary with case-folded collision suffixes (`_2`, `_3`).
  - Pass 2 renders articles using resolved slugs directly for link targets.
- **Atomic Writes & Orphan Sweeping**:
  - `write_text_atomic_if_changed(path, text)` writes only when bytes differ.
  - Sweeps stale generated community/god-node files not in current run manifest.

### 3. CLI Command Group (`src/buddhi/commands/docs.py`) & Site Orchestrator (`src/buddhi/docgen/site.py`)

- **Typer Setup**:
  - `docs_app = typer.Typer(invoke_without_command=True, help="...")`
  - Default callback executes `buddhi docs`: triggers graph freshness check -> OKF synthesis -> Pelican static compile -> HTTP server.
  - `buddhi docs serve`: Explicit live server command (`--host`, `--port`, `--open/--no-open`, `--reload/--no-reload`).
  - `buddhi docs build`: One-shot static compilation into `.buddhi/site/` (or `--output`).
  - `buddhi docs plan`: Enriched `.buddhi/docs-plan.json` generation (backward-compatible).
- **Pelican Programmatic Configuration (`site.py`)**:
  - Dynamically builds Pelican settings dictionary (`PATH`, `OUTPUT_PATH`, `THEME`, `READERS`, `PAGE_PATHS=["."]`, `ARTICLE_PATHS=[]`, `RELATIVE_URLS=True`).
  - Executes `Pelican(settings).run()`.
  - Generates `.buddhi/site/search-index.json`.
  - Copies/links `.buddhi/graphs/tree-graph.html` into `.buddhi/site/graphs/tree-graph.html`.
- **Live Server Execution**:
  - Pre-bind socket probe checks port availability.
  - Serves via `RootedHTTPServer(output_dir, (host, port), ComplexHTTPRequestHandler)`.
  - Background thread watches `.buddhi/docs/` and triggers incremental recompilation on changes.

### 4. Client-Side Search Engine (`src/buddhi/docgen/theme/static/js/search.js`)

- **Index Format (`search-index.json`)**:
  ```json
  [
    {
      "title": "build_docs_plan",
      "kind": "function",
      "summary": "Compute the ordered, staleness-annotated doc plan for graph.",
      "url": "symbols/buddhi/docgen/planner/build_docs_plan.html",
      "tags": ["python", "src/buddhi/docgen/planner.py"],
      "community": "docgen-pipeline"
    }
  ]
  ```
- **UI & Keyboard Interaction**:
  - WAI-ARIA combobox with `aria-activedescendant` result navigation.
  - Keyboard triggers: `/` or `Ctrl+K` focuses input; `ArrowUp`/`ArrowDown` navigates; `Enter` opens page; `Esc` dismisses.
  - Three distinct UI states: Loading, Empty, Error.

---

## Accessibility Strategy (WCAG 2.2 AA / Standard Profile)

Complies with project `.agents/rules/a11y.md` and `.agents/skills/a11y/SKILL.md`:

1. **Semantic Landmarks & ARIA**:
   - Distinct HTML5 landmarks: `<header>`, `<nav aria-label="Documentation Navigation">`, `<nav aria-label="Breadcrumb">`, `<main id="main-content">`, `<aside aria-label="Table of Contents">`, `<footer>`.
   - Skip to main content link positioned at start of page body.
   - Zero redundant ARIA roles on native elements.
2. **Color Contrast Floors (Tested with `buddhi scripts contrast`)**:
   - Light Theme: Primary text (`#0f172a` on `#ffffff`) at **17.85:1** (exceeds 4.5:1); secondary text (`#475569` on `#ffffff`) at **7.58:1**; UI borders (`#64748b` on `#ffffff`) at **4.76:1** (exceeds 3.0:1).
   - Dark Theme: Primary text (`#f1f5f9` on `#0b0f19`) at **17.48:1**; secondary text (`#94a3b8` on `#0b0f19`) at **7.47:1**; UI borders (`#64748b` on `#0b0f19`) at **4.02:1**.
3. **Keyboard Operability & Focus Rings**:
   - Universal `:focus-visible` styling (`outline: 2px solid var(--color-focus-ring); outline-offset: 2px;`).
   - No mouse-only interactions; full dialog trap and Escape dismissal in search modal.
4. **Static Verification Gate**:
   - Validated via `uv run buddhi scripts verify-a11y . --src src/buddhi/docgen/theme/` and `uv run buddhi scripts contrast --css src/buddhi/docgen/theme/static/css/theme.css`.

---

## Automated Verification & Test Strategy

Mapped to Success Criteria `SC-001` through `SC-005`:

1. **`tests/test_docgen_reader.py`**:
   - Parse nested OKF frontmatter (`sources`, `relations`, `generated`, `tags`).
   - Confirm stripping of forbidden Attested Computation fields.
   - Verify Markdown extension rendering (code highlighting, tables, TOC).
   - Verify relative `.md` link rewriting to `.html` while preserving external/anchor links.
2. **`tests/test_docgen_generator.py`**:
   - Synthesize `index.md`, `architecture-report.md`, communities, god nodes from SQLite graph fixture.
   - Confirm existing LLM symbol docs are preserved when `content_hash` matches.
   - Confirm Windows `MAX_PATH` length cap and case-insensitive suffix collision handling (`parser.md` vs `parser_2.md`).
   - Confirm `write_text_atomic_if_changed` results in 0 file writes on second run (`SC-003`).
   - Confirm orphan sweeping removes stale generated files without touching symbol docs.
3. **`tests/test_commands_docs.py`**:
   - `test_docs_build_full_lifecycle`: End-to-end static build produces `.buddhi/site/index.html` and `search-index.json` in <10s (`SC-001`).
   - `test_compiled_site_link_integrity_crawler`: Crawler visits all `<a href>` targets in compiled HTML and asserts zero 404s (`SC-002`).
   - `test_theme_a11y_and_contrast_gates`: Runs `verify_a11y` and `contrast` on theme (`SC-004`).
   - `test_docs_serve_ephemeral_port`: Starts server on test port, executes HTTP GET, validates response, verifies clean shutdown.
4. **Quality Gate Execution**:
   - `uv run pytest`
   - `uv run ruff check .`
   - `uv run mypy src/ tests/` (`SC-005`).

---

## Complexity Tracking

| Architectural Trade-Off | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Custom Reader (`OKFMarkdownReader`) instead of standard Pelican MarkdownReader** | Google OKF v0.2 uses nested YAML structures (`sources: [{id, resource, content_hash}]`, `generated: {...}`) for provenance. | Python-markdown's flat `meta` extension only parses `key: value` lines, silently mangling or discarding OKF nested dictionaries and lists. |
| **Two-pass slug resolution with case-folding** | Cross-platform integrity: on Windows (NTFS) and macOS (APFS), files differencing only by case collide. | Single-pass or lowercase-only slugging either overwrites files unexpectedly or mangles distinct qualified symbols. |
| **Atomic write by byte comparison (`write_text_atomic_if_changed`)** | Pelican's live server monitors file `mtime` to trigger rebuilds. | Direct writes touch filesystem timestamps even when bytes are unchanged, creating infinite watcher rebuild loops. |
