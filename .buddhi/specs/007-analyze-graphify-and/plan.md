# Implementation Plan: Graphify-Inspired Code Graph Intelligence, Blast Radius Analysis & Antigravity SDD Integration

**Branch**: `007-analyze-graphify-and` | **Date**: 2026-10-27 | **Spec**: [spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/007-analyze-graphify-and/spec.md)

**Input**: Feature specification from `/.buddhi/specs/007-analyze-graphify-and/spec.md`

---

## Summary

Upgrade `buddhi-cli`'s code graph engine, MCP server, CLI, Spec-Driven Development (SDD) workflow, and Google Antigravity customizations (`skills`, `rules`, `subagents`, `hooks`) using clean-room native algorithms inspired by `graphify` (`https://github.com/Graphify-Labs/graphify`, Apache-2.0 / MIT):

1. **Deep Cross-File Resolution, Confidence Tiers, Leiden Cohesion & Incremental Caching (`P1`)**:
   - Extend tree-sitter `.scm` queries across all 9 supported languages to capture base classes/interfaces/traits (`@inherit.base`) and named imports (`@import.symbol`).
   - Build a project-wide `SymbolIndex` in `src/buddhi/graph/resolver.py` to resolve cross-file calls and `INHERITS` edges with provenance confidence (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`), `confidence_score` (`0.1–1.0`), and `context` (`call`, `import`, `inherit`, `type_ref`, `contains`).
   - Upgrade `src/buddhi/graph/clustering.py` with canonical edge sorting (100% hash-seed determinism), super-hub exclusion (`degree > max(50, p99_degree)`) with neighbor-majority reattachment, oversized/low-cohesion sub-splitting, per-community `cohesion` scores, and deterministic hub-based `label`s stored in SQLite Schema v2 (`communities` table).
   - Add SHA-256 per-file AST extraction caching (`extract_cache` table inside `.buddhi/graphs/tree-graph.db` carried forward across atomic rebuilds) and `meta.built_at_commit` git `HEAD` tracking.
2. **Blast Radius Engine, Topological Analytics & Token-Bounded MCP Retrieval (`P2`)**:
   - Create `src/buddhi/graph/blast_radius.py` (`compute_blast_radius` for files, symbols, or `git diff` via working tree, `--staged`, or `--git-ref`, computing direct/transitive callers via Hub-Blocked Reverse BFS, affected Leiden communities with cohesion, impacted `god_nodes`, crossed bridges, new import cycles, and risk classification).
   - Create `src/buddhi/graph/analyze.py` (`get_god_nodes`, `get_surprising_connections`, `suggest_questions`, `find_shortest_path` with disambiguation, `find_import_cycles`, `get_community_detail`, `get_graph_stats`).
   - Expose unified `buddhi_graph` MCP tool (`src/buddhi/mcp/tools/graph.py` + `src/buddhi/mcp/server.py`) and `buddhi graph` Typer CLI command group (`src/buddhi/commands/graph_cmd.py` + `src/buddhi/cli.py`).
   - Upgrade `buddhi_search` (`src/buddhi/mcp/tools/search.py`) with IDF-weighted multi-field scoring + squared term coverage `(matched_terms / total_terms)^2` and Hub-Blocked 2-Hop BFS to eliminate full-community memory explosion.
3. **Graph-Driven SDD Workflow Integration (`P3`)**:
   - Add `src/buddhi/sdd/impact.py` (`buddhi sdd impact`) and enhance `src/buddhi/sdd/setup_plan.py` (`buddhi sdd setup-plan`) to inject a quantitative `GRAPH_CONTEXT` (communities, cohesion, god nodes, bridges, import cycles, review questions) into SDD planning and verification while keeping codebase documentation strictly in existing OKF v0.2 `.buddhi/docs/` format.
4. **Official Antigravity Customizations & Attribution (`P4`)**:
   - Add official Antigravity YAML frontmatter (`description`, `trigger: always_on` / `glob`) to `.agents/rules/*.md` and `src/buddhi/templates/agents/rules/*.md`.
   - Equip specialist subagents (`.agents/agents/*.md` and templates) with `buddhi_search`, `buddhi_read`, `buddhi_graph`, and `buddhi_memory` tools.
   - Add stdlib-only, fail-open, `<50ms` `graph_context.py` hook registered in `.agents/hooks.json` (and template) for `SessionStart` (graph/memory staleness) and `PreToolUse` (injecting file symbols, community label/cohesion, caller/callee counts, and active path-scoped OKF memories via `additionalContext`).
   - Update `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, `README.md`, and `.gitignore` (ensuring `./temp/` is ignored and never staged).

---

## Technical Context

**Language/Version**: Python >= 3.10

**Primary Dependencies**: `typer >= 0.12.5`, `rich >= 13.7.0`, `tree-sitter >= 0.25.0` (+ language grammars), `igraph >= 0.11.0`, `mcp >= 1.2.0` (`FastMCP`), `pathspec >= 0.12.1`, Python stdlib (`sqlite3`, `hashlib`, `json`, `subprocess`, `pathlib`)

**Storage**: Single SQLite database at `.buddhi/graphs/tree-graph.db` (Schema v2: `nodes`, `edges`, `communities`, `extract_cache`, `meta`), Cytoscape JSON (`.buddhi/graphs/tree-graph.json`), interactive HTML (`.buddhi/graphs/tree-graph.html`)

**Testing**: `pytest >= 8.0.0`, `ruff >= 0.5.0`, `mypy >= 1.10.0`, `buddhi scripts check-file-size --all`

**Target Platform**: Cross-platform CLI & MCP Server (Windows, macOS, Linux) integrated with Google Antigravity IDE / CLI

**Project Type**: CLI / Agent Harness Generator & MCP Server (`buddhi-ai`)

**Performance Goals**:
- `PreToolUse` hook (`graph_context.py`): `< 50ms` p95 execution time, stdlib-only cold start, 100% fail-open (`exit 0`).
- `SessionStart` hook (`graph_context.py`): `< 100ms` execution time, pure-Python `.git/HEAD` resolution with subprocess fallback.
- Incremental `buddhi generate`: `100%` tree-sitter parse skip rate on unchanged files via SHA-256 `extract_cache`.
- `buddhi_search`: strictly bounded by `budget` characters (`<= budget * 4` chars / `budget` tokens) regardless of Leiden community size.

**Constraints**:
- File-size ratchet: Every source file under `src/buddhi/` MUST remain strictly `< 8,000 tokens` (`32 KB`).
- Zero new external PyPI dependencies required.
- Codebase concept documentation remains strictly governed by OKF v0.2 under `.buddhi/docs/`.
- `./temp/graphify/` MUST never be indexed into `buddhi-cli`'s own repo graph or staged/committed to git.

**Scale/Scope**: Repositories up to 50k+ symbols and 200k+ edges; 9 AST languages; 8 MCP graph actions; 6 CLI `buddhi graph` subcommands; 11 SDD/harness skills; 4 rules; 7 specialist subagents; 2 lifecycle hooks.

---

## AGENTS.md Compliance Check

*GATE: Passed before Phase 0 research and re-verified after Phase 1 design.*

- [x] **Project build & test commands adhered to**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/ tests/` executed via `terminal-runner`.
- [x] **Architectural constraints respected**: Clean-room modular architecture under `src/buddhi/`, keeping every file well below the 8,000-token ratchet; backward-compatible SQLite reader introspection for Schema v1 databases.
- [x] **No unapproved external dependencies introduced**: Built entirely on existing `sqlite3`, `igraph`, `tree-sitter`, `FastMCP`, and `typer`.

---

## Multi-Angle Architectural Evaluation (Three Lenses)

1. **Fewest-Slices Lens (Minimal Viable End-to-End Value)**:
   - Consolidate all new persistence tables (`communities`, `extract_cache`) and edge columns (`confidence`, `confidence_score`, `context`) into the existing `.buddhi/graphs/tree-graph.db` atomic writer (`sqlite_writer.py`) rather than introducing a second database file or external cache daemon.
   - Expose all 8 topological and blast-radius operations through one unified `buddhi_graph(action=...)` MCP tool (matching `buddhi_memory(action=...)`) and one `buddhi graph` CLI group.
2. **Risk-First Lens (De-Risking Volatility Early)**:
   - *Risk 1 — Community & Hub Explosion*: Large utility hubs (`Logger`, `Config`, `get_db`) collapse Leiden clusters and cause 2-hop BFS in `buddhi_search` and `blast_radius` to pull in the entire repository. **Mitigation**: Exclude super-hubs (`degree > max(50, p99_degree)`) during initial Leiden partitioning (reattaching by neighbor majority) and block BFS transit hops *through* super-hubs while still reporting them in `impacted_god_nodes`.
   - *Risk 2 — Windows SQLite Locking & Hook Latency*: Hook scripts importing heavy packages (`igraph`, `tree_sitter`, `typer`) take 300ms+ on Windows and can contend with `os.replace`. **Mitigation**: `graph_context.py` uses Python stdlib only, opens `tree-graph.db` via read-only URI (`?mode=ro`, `timeout=0.03`), closes connections immediately, and `write_sqlite()` retries `os.replace` with a short backoff on Windows `PermissionError`.
   - *Risk 3 — Git Option Injection & Untrusted Stdin*: `--git-ref` could receive a leading `-` flag (`--upload-pack=...`). **Mitigation**: Strict regex allowlist (`^[A-Za-z0-9_./~^@-]{1,128}$` and `not startswith("-")`), `shell=False`, and `timeout=5.0`.
3. **Seam-Quality Lens (Clean Boundaries & Zero Leaked Internals)**:
   - Strip transient `tree_sitter.Node` objects from `ExtractedFile` immediately after `extract_file()` so `ExtractedFile` is a pure value object serializable via `json.dumps` / `json.loads` (no `pickle`).
   - Provide `get_db_capabilities(conn)` in `sqlite_writer.py` / `analyze.py` so MCP tools, CLI commands, and hooks work seamlessly against both Schema v1 and Schema v2 SQLite files.

---

## System Design Record: Storage & Cache Architecture

### Decision: Single SQLite Database (`tree-graph.db` Schema v2) vs. Separate Cache File

- **Context**: `write_sqlite()` atomically writes a fresh `.tmp-<pid>` SQLite file and replaces `.buddhi/graphs/tree-graph.db`. We need durable storage for `communities` metadata and SHA-256 per-file AST `extract_cache`.
- **Alternatives Considered**:
  1. **Option A (Selected — Single `tree-graph.db` Schema v2)**: Store `nodes`, `edges`, `communities`, `extract_cache`, and `meta` in `.buddhi/graphs/tree-graph.db`. Before building the graph, `run_pipeline()` loads existing `extract_cache` rows from `tree-graph.db`; during `write_sqlite()`, active cache rows are written into `.tmp-<pid>` inside the same transaction.
  2. **Option B (Separate `.buddhi/graphs/extract-cache.db` or JSON file)**: Keep a second file on disk next to `tree-graph.db`.
- **Trade-offs & Rationale**: Option A keeps `.buddhi/graphs/` clean with a single SQLite file, guarantees atomic consistency between `nodes`/`edges` and `extract_cache`, automatically prunes deleted files on rebuild, and uses pure `json.dumps`/`json.loads` payloads inside SQLite for security.

---

## Database Schema & Query Design (`.buddhi/graphs/tree-graph.db` Schema v2)

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = MEMORY;
PRAGMA synchronous = OFF;

CREATE TABLE nodes (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    name            TEXT NOT NULL,
    qualified_name  TEXT,
    file_path       TEXT,
    language        TEXT,
    start_line      INTEGER,
    end_line        INTEGER,
    parent_id       TEXT REFERENCES nodes(id) ON DELETE CASCADE,
    signature       TEXT,
    external        INTEGER NOT NULL DEFAULT 0 CHECK (external IN (0, 1)),
    snippet         TEXT,
    community_id    INTEGER
);

CREATE INDEX idx_nodes_parent       ON nodes(parent_id);
CREATE INDEX idx_nodes_kind         ON nodes(kind);
CREATE INDEX idx_nodes_file         ON nodes(file_path);
CREATE INDEX idx_nodes_community    ON nodes(community_id) WHERE community_id IS NOT NULL;
CREATE INDEX idx_nodes_name_lower   ON nodes(LOWER(name), external);
CREATE INDEX idx_nodes_qname_lower  ON nodes(LOWER(qualified_name), external);

CREATE TABLE edges (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id        TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    kind             TEXT NOT NULL,
    resolved         INTEGER NOT NULL DEFAULT 1 CHECK (resolved IN (0, 1)),
    confidence       TEXT NOT NULL DEFAULT 'EXTRACTED'
                     CHECK (confidence IN ('EXTRACTED', 'INFERRED', 'AMBIGUOUS')),
    confidence_score REAL NOT NULL DEFAULT 1.0
                     CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    context          TEXT NOT NULL DEFAULT 'contains'
                     CHECK (context IN ('call', 'import', 'inherit', 'type_ref', 'contains'))
);

CREATE INDEX idx_edges_kind_source   ON edges(kind, source_id);
CREATE INDEX idx_edges_kind_target   ON edges(kind, target_id);
CREATE INDEX idx_edges_source_target ON edges(source_id, target_id, kind);
CREATE INDEX idx_edges_confidence    ON edges(confidence) WHERE confidence != 'EXTRACTED';

CREATE TABLE communities (
    id          INTEGER PRIMARY KEY,
    label       TEXT NOT NULL,
    node_count  INTEGER NOT NULL CHECK (node_count >= 0),
    cohesion    REAL NOT NULL CHECK (cohesion >= 0.0 AND cohesion <= 1.0),
    hub_node_id TEXT REFERENCES nodes(id) ON DELETE SET NULL,
    top_files   TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE extract_cache (
    file_path    TEXT PRIMARY KEY,
    sha256       TEXT NOT NULL,
    language     TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE INDEX idx_extract_cache_sha256 ON extract_cache(file_path, sha256);

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
```

---

## Project Structure

### Documentation (this feature)

```text
.buddhi/specs/007-analyze-graphify-and/
├── spec.md              # Feature specification (/specify output)
├── plan.md              # Architectural implementation plan (/spec-plan output)
└── tasks.md             # Story-scoped task breakdown (/spec-tasks output)
```

### Source Code (repository root)

```text
src/buddhi/
├── cli.py                                  # Register `graph_app` ("graph")
├── commands/
│   ├── generate.py                         # Pass existing db_path for SHA-256 cache & print cache stats
│   ├── graph_cmd.py                        # NEW: `buddhi graph` CLI (blast-radius, analyze, path, cycles, community, stats)
│   ├── init.py                             # Pass db_path for cache, merge hooks.json & rule frontmatter idempotently
│   └── sdd.py                              # Register `buddhi sdd impact` subcommand
├── discovery/
│   └── walker.py                           # Add "temp" and ".agents" to DEFAULT_EXCLUDED_DIRS
├── graph/
│   ├── model.py                            # Extend GraphEdge (confidence, confidence_score, context), add CommunityInfo & CodeGraph fields
│   ├── extractor.py                        # Add RawInheritance, imported_names on RawImport, pure-value ExtractedFile
│   ├── cache.py                            # NEW: SHA-256 extract_cache SQLite load/serialize & get_git_head_sha()
│   ├── builder.py                          # Wire cache hit/miss, collect PendingInheritance, tag CONTAINS edges
│   ├── resolver.py                         # Project-wide SymbolIndex, cross-file CALLS & INHERITS resolution, confidence tiers
│   ├── clustering.py                       # Canonical edge sorting, super-hub exclusion/reattach, sub-splitting, cohesion & hub naming
│   ├── pipeline.py                         # Coordinate extract_cache load -> build -> resolve -> cluster -> built_at_commit
│   ├── analyze.py                          # NEW: god_nodes, surprising_connections, suggest_questions, shortest_path, find_import_cycles, community, stats
│   └── blast_radius.py                     # NEW: compute_blast_radius (files, symbols, git diff, Hub-Blocked Reverse BFS, risk_level)
├── languages/
│   └── queries/
│       ├── python.scm                      # Add @inherit.base & @import.symbol captures
│       ├── typescript.scm                  # Add @inherit.base & @import.symbol captures
│       ├── javascript.scm                  # Add @inherit.base & @import.symbol captures
│       ├── go.scm                          # Add struct embedding @inherit.base captures
│       ├── rust.scm                        # Add trait impl @inherit.base captures
│       ├── java.scm                        # Add superclass/interfaces @inherit.base captures
│       ├── kotlin.scm                      # Add delegation_specifier @inherit.base captures
│       ├── csharp.scm                      # Add base_list @inherit.base captures
│       └── swift.scm                       # Add inheritance_specifier @inherit.base captures
├── mcp/
│   ├── server.py                           # Register `buddhi_graph` tool on FastMCP server
│   └── tools/
│       ├── graph.py                        # NEW: `execute_buddhi_graph` action dispatcher & Markdown/JSON formatter
│       └── search.py                       # Upgrade `execute_buddhi_search` with IDF + squared coverage & Hub-Blocked 2-Hop BFS
├── persist/
│   ├── sqlite_writer.py                    # Schema v2 (edges confidence/context, communities, extract_cache, meta.built_at_commit)
│   └── json_writer.py                      # Include confidence, confidence_score, context, and communities in Cytoscape JSON
├── sdd/
│   ├── setup_plan.py                       # Inject GRAPH_CONTEXT topological summary when tree-graph.db exists
│   └── impact.py                           # NEW: SDD topological & blast-radius impact helper (`buddhi sdd impact`)
├── templates/
│   └── agents/
│       ├── hooks.json                      # Register `graph_context.py` on SessionStart and PreToolUse
│       ├── hooks/
│       │   ├── guard_destructive.py
│       │   └── graph_context.py            # NEW: Stdlib-only <50ms fail-open graph & memory context injector
│       ├── rules/
│       │   ├── harness-core.md             # Official YAML frontmatter (`trigger: always_on`) + `buddhi_graph` protocol
│       │   ├── okf-docs.md                 # Official YAML frontmatter (`trigger: always_on`)
│       │   ├── a11y.md                     # Official YAML frontmatter (`trigger: always_on`)
│       │   └── antislop.md                 # Official YAML frontmatter (`trigger: always_on`)
│       ├── agents/
│       │   └── *.md                        # Add `buddhi_search`, `buddhi_read`, `buddhi_graph`, `buddhi_memory` to tools & prompts
│       ├── skills/
│       │   └── {specify,explore-unknowns,spec-plan,spec-tasks,implement,verify,close-spec,ask,debug,status,okf-context}/SKILL.md
│       └── templates/
│           └── plan-template.md            # Add Topological & Blast Radius Grounding section
└── util/
    └── fsutil.py                           # Idempotent hook merger (`ensure_graph_context_hook`) & rule frontmatter sync

tests/
├── test_extractor_languages.py             # Extend with inheritance & symbol import tests across languages
├── test_resolver.py                        # Extend with cross-file CALLS, INHERITS, confidence tiers & ambiguity tests
├── test_clustering.py                      # Extend with PYTHONHASHSEED determinism, super-hub exclusion, cohesion & hub labels
├── test_sqlite_writer.py                   # Extend with Schema v2 tables, extract_cache hit/miss, built_at_commit
├── test_graph_analyze.py                   # NEW: Unit/integration tests for analyze.py & blast_radius.py
├── test_cli_graph.py                       # NEW: CLI tests for `buddhi graph` subcommands
├── test_mcp_server.py                      # Extend with `buddhi_graph` tool tests across all 8 actions
├── test_search.py                          # Extend with IDF scoring, Hub-Blocked 2-Hop BFS & token budget cap tests
├── test_sdd.py                             # Extend with `setup-plan` GRAPH_CONTEXT & `buddhi sdd impact` tests
└── test_hook_graph_context.py              # NEW: Subprocess tests for `graph_context.py` SessionStart & PreToolUse
```

**Structure Decision**: Single-project modular Python package (`src/buddhi/` + `tests/`), splitting new graph analytics into `cache.py`, `analyze.py`, `blast_radius.py`, `mcp/tools/graph.py`, `commands/graph_cmd.py`, and `sdd/impact.py` so every file stays between ~1,200 and ~3,200 tokens (well under the 8,000-token ceiling).

---

## Complexity Tracking

| Trade-off / Design Choice | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Splitting `analyze.py` and `blast_radius.py` into two modules | Keeps each module under ~2,600 tokens (well below the 8,000-token ratchet) and separates static topology diagnostics from git-diff blast radius traversal | Putting all 8 actions in one file would approach 6,000+ tokens and mix git subprocess diffing with pure SQLite graph metrics |
| Stdlib-only `graph_context.py` hook querying SQLite directly | Guarantees `<50ms` `PreToolUse` latency on Windows without importing `typer`/`igraph`/`tree_sitter` | Invoking `uv run buddhi ...` from a `PreToolUse` hook would add 400–800ms per tool call |
