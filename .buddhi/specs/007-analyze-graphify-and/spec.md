# Feature Specification: Graphify-Inspired Code Graph Intelligence, Blast Radius Analysis & Antigravity SDD Integration

**Feature Branch**: `007-analyze-graphify-and`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Analyze the `graphify` project located in `./temp/graphify/` and see the licensing of the repo to verify that code and the idea in this repo can be reused without any legal issue. If it is permitted, analyze that project to understand how it is implemented for AI coding assistants. Then improve the existing code graph implementation in `buddhi-cli` getting inspiration and guidance from `graphify`. Suggest all possible improvements and integrate the code graph to Spec Driven Development workflow in `buddhi-cli` adhering to the best practices for Antigravity. Follow official Antigravity documentation for extending Antigravity capabilities (Skills, Rules, Subagents, Hooks). Update `ACKNOWLEDGMENTS.md`, `CHANGELOG.md` under `[Unreleased]`, and `README.md`."

---

## Legal & Licensing Assessment Summary

1. **Upstream License (`./temp/graphify/`)**:
   - Package: `graphifyy` (`https://github.com/Graphify-Labs/graphify`, Author: Safi Shamsi).
   - Dual/Transitioned Permissive Licensing: **Apache License 2.0** (`LICENSE`, `NOTICE`) with prior contributions retained under **MIT License** (`LICENSE-MIT`, `Copyright (c) 2026 Safi Shamsi`).
2. **Compatibility with `buddhi-cli` (MIT License)**:
   - Under copyright law (17 U.S.C. § 102(b)) and permissive open-source licensing (Apache-2.0 / MIT), architectural concepts, graph schemas, topological heuristics, scoring equations (IDF + squared coverage, surprise score, cohesion score, hub-blocked BFS, confidence tiers), and workflow patterns can be freely adapted and re-implemented natively on `buddhi-cli`'s `CodeGraph` + SQLite (`tree-graph.db`) + `igraph` + FastMCP stack without legal or licensing conflict.
   - `ACKNOWLEDGMENTS.md` already attributes both Apache-2.0 (`Google Open Knowledge Format (OKF)`) and MIT (`anti-slop`, `A11Y.md`, `dzhng/skills`) projects; adding a dedicated `Graphify` section with full attribution, NOTICE, and license text satisfies all attribution best practices.
   - **Strict Workspace Invariant**: Nothing from `./temp/` (`./temp/graphify/`) shall ever be staged or committed to git. Codebase documentation remains strictly governed by `buddhi-cli`'s existing OKF v0.2 `.buddhi/docs/` system (excluding `graphify`'s separate `GRAPH_REPORT.md` / wiki / multi-modal Whisper/PDF/image extractors).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deep Cross-File Resolution, Confidence Tiers, Named Leiden Communities & Incremental Caching (Priority: P1)

As a developer or AI coding agent running `buddhi generate` or `buddhi init`, I need the code graph (`tree-graph.db`, `tree-graph.json`, `tree-graph.html`) to resolve cross-file function/method calls and class/interface inheritance across the project, tag edges with provenance confidence (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`) and context (`call`, `import`, `inherit`, `type_ref`), produce deterministic and human-named Leiden communities with cohesion scores, and cache per-file AST extractions by SHA-256 alongside the git `built_at_commit` SHA so graph rebuilds are accurate, deterministic, and fast.

**Why this priority**: Every downstream capability — MCP retrieval, Blast Radius analysis, topological diagnostics, SDD impact planning, and Antigravity hooks — depends on accurate cross-file edges and well-formed communities in `tree-graph.db`. Currently, `resolver.py` only resolves same-file calls and `self.`/`this.` calls (turning cross-file calls into unresolved `external:` stubs) and never emits `INHERITS` edges despite `clustering.py` weighting them at `10.0`.

**Independent Test**: Run `uv run buddhi generate` on a multi-file repository (and unit test fixtures with cross-file imports, function calls, and class inheritance) and query `.buddhi/graphs/tree-graph.db` to verify resolved cross-file `CALLS` and `INHERITS` edges, edge `confidence` / `confidence_score` / `context` columns, the `communities` table (`id`, `label`, `node_count`, `cohesion`, `hub_node_id`), `meta.built_at_commit`, and SHA-256 cache hits on repeat runs.

**Acceptance Scenarios**:

1. **Given** a multi-file codebase where `module_a.py` imports `helper` from `module_b.py` and calls `helper()`, and `ClassA` inherits from `BaseB`, **When** `buddhi generate` runs, **Then** `tree-graph.db` contains a resolved `CALLS` edge from the caller in `module_a.py` to `module_b.py::helper` and a resolved `INHERITS` edge from `ClassA` to `BaseB` with `confidence` (`EXTRACTED` or `INFERRED`), `confidence_score` (`0.55–1.0`), and `context` (`call`, `inherit`).
2. **Given** a codebase with utility super-hubs and varying module sizes, **When** `clustering.py` runs Leiden clustering, **Then** edges are sorted canonically for 100% hash-seed determinism, super-hubs above the 99th percentile (`max(50, p99_degree)`) are excluded during initial partitioning and reattached by neighbor majority vote, oversized (`>25%` of nodes) or low-cohesion (`cohesion < 0.05`) communities are sub-split, and each community is recorded in the `communities` table with a deterministic hub-based `label` and `cohesion` score (`0.0–1.0`).
3. **Given** an already-generated code graph where only 1 of 100 files was modified, **When** `buddhi generate` runs again, **Then** unchanged files are loaded from the SHA-256 AST extraction cache without re-parsing tree-sitter ASTs, and `meta` stores `built_at_commit` matching `git rev-parse HEAD`.

---

### User Story 2 - Topological Analytics, Blast Radius Engine & Token-Bounded MCP Retrieval (Priority: P2)

As an AI coding agent or developer investigating architecture or evaluating a change, I need a unified `buddhi_graph` MCP tool and `buddhi graph` CLI command group providing **Blast Radius (`blast_radius`)** analysis, `god_nodes`, `surprising_connections` (`surprises`), `suggest_questions` (`questions`), `shortest_path` (`path`), `find_import_cycles` (`cycles`), `get_community` (`community`), and `graph_stats` (`stats`), alongside an upgraded `buddhi_search` that uses IDF-weighted multi-term scoring and Hub-Blocked 2-Hop BFS instead of dumping entire Leiden communities into memory.

**Why this priority**: Directly delivers the user-requested **Blast Radius** capability and `graphify`-inspired topological intelligence while eliminating `buddhi_search`'s community-explosion bottleneck.

**Independent Test**: Invoke `buddhi graph blast-radius`, `buddhi graph analyze`, `buddhi graph path`, `buddhi graph stats` via CLI (`--json`) and call `buddhi_graph` and `buddhi_search` via FastMCP unit/integration tests to verify accurate blast-radius impact reports, topological diagnostics, and bounded token usage.

**Acceptance Scenarios**:

1. **Given** a list of modified files, symbol IDs, or a `git diff` reference (`--git-ref HEAD~1` or staged/unstaged working tree changes), **When** `buddhi graph blast-radius` or `buddhi_graph(action="blast_radius", ...)` is called, **Then** it returns direct and transitive callers/dependents (up to configurable hop depth), affected Leiden communities with their cohesion scores, impacted `god_nodes`, cross-community bridge edges crossed, newly introduced import cycles, and an overall risk tier (`low`, `medium`, `high`, `critical`).
2. **Given** a populated `tree-graph.db`, **When** `buddhi_graph` is invoked with `action` in `{"god_nodes", "surprises", "questions", "shortest_path", "cycles", "community", "stats"}`, **Then**:
   - `god_nodes` returns top architectural hubs excluding file/directory containers and builtin noise labels.
   - `surprises` ranks cross-community, cross-directory, peripheral-to-hub, and inferred bridges by composite surprise score.
   - `questions` synthesizes architectural review questions across 5 diagnostic categories (`ambiguous_edge`, `bridge_node`, `verify_inferred`, `isolated_nodes`, `low_cohesion`).
   - `shortest_path` finds the shortest directed/undirected relational path between two symbols (with tiered disambiguation if symbol names are ambiguous).
   - `cycles` reports file-level circular `IMPORTS` chains.
   - `stats` reports node/edge/community counts, confidence breakdown, and git `HEAD` vs `built_at_commit` staleness.
3. **Given** a multi-term query in `buddhi_search`, **When** anchor nodes belong to a large Leiden community, **Then** `buddhi_search` scores candidates using IDF-weighted multi-field matching (`exact`, `prefix`, `substring`, `file_path`) with squared term coverage `(matched_terms / total_terms)^2` and expands neighbors via Hub-Blocked 2-Hop BFS (skipping transit through super-hubs with `degree > max(50, p99_degree)`), staying strictly within `token_budget`.

---

### User Story 3 - Graph-Driven Spec-Driven Development (SDD) Workflow Integration (Priority: P3)

As a developer or agent using `buddhi-cli`'s SDD workflow (`/specify`, `/explore-unknowns`, `/spec-plan`, `/spec-tasks`, `/implement`, `/verify`, `/close-spec`), I need the code graph and Blast Radius engine integrated into SDD CLI commands and skills so specifications uncover architectural unknowns, plans ground their 3 slicing lenses (*Fewest-slices*, *Risk-first*, *Seam-quality*) in real community/hub/bridge metrics, and verification proves that the blast radius of `git diff` is covered by tests with zero new import cycles.

**Why this priority**: Connects the upgraded code graph and Blast Radius engine directly to `buddhi-cli`'s signature SDD lifecycle so agents make grounded architectural decisions automatically.

**Independent Test**: Run `buddhi sdd setup-plan --json` and `buddhi sdd impact --json` (or `buddhi graph blast-radius --git-ref`) in a test repo and inspect updated SDD skills (`specify`, `explore-unknowns`, `spec-plan`, `spec-tasks`, `implement`, `verify`, `close-spec`) to confirm topological context and blast-radius gates are present and functional.

**Acceptance Scenarios**:

1. **Given** a user starting `/specify` or `/explore-unknowns` on a subsystem, **When** step 3 (Codebase grounding) runs, **Then** the agent uses `buddhi_graph(action="questions")` and `buddhi_graph(action="community")` alongside OKF `.buddhi/docs/` to surface low-cohesion modules, bridge nodes, and ambiguous dependencies during clarification.
2. **Given** a feature branch with `spec.md`, **When** `/spec-plan` (`buddhi sdd setup-plan`) executes, **Then** a **Topological & Blast Radius Context Summary** (relevant communities, cohesion scores, god nodes, cross-community bridges, and existing import cycles) is computed and provided to specialist subagents so the *Fewest-slices*, *Risk-first*, and *Seam-quality* lenses are grounded in quantitative graph topology.
3. **Given** an implemented feature during `/implement` or `/verify`, **When** verification runs, **Then** `buddhi graph blast-radius` analyzes the `git diff` to list all impacted transitive callers, affected communities, and touched god nodes, verifying that affected contracts have test evidence and no new circular import chains were introduced.

---

### User Story 4 - Official Antigravity Customizations (Skills, Rules, Subagents, Hooks) & Documentation Updates (Priority: P4)

As an Antigravity IDE / CLI user running `buddhi init`, I need all scaffolded Skills (`.agents/skills/`), Rules (`.agents/rules/`), Subagents (`.agents/agents/`), and Hooks (`.agents/hooks.json` + `.agents/hooks/`) to follow official Google Antigravity documentation, including explicit rule frontmatter triggers, MCP-enabled specialist subagents, and non-blocking `SessionStart` / `PreToolUse` hooks that inject graph staleness, file symbol/community topology, and active OKF memory context via `additionalContext`, plus updated `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`.

**Why this priority**: Ensures the harness adheres strictly to official Antigravity customization specifications (`skills`, `rules`, `subagents`, `hooks`) and fulfills all attribution and documentation requirements.

**Independent Test**: Run `buddhi init` in a workspace, validate `.agents/rules/*.md` YAML frontmatter, `.agents/agents/*.md` tool declarations, `.agents/skills/*/SKILL.md` frontmatter, execute `.agents/hooks/graph_context.py` on sample `SessionStart` and `PreToolUse` JSON stdin payloads to verify `<100ms` fail-open `additionalContext` JSON stdout, and verify `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md`.

**Acceptance Scenarios**:

1. **Given** `.agents/rules/*.md` in both `src/buddhi/templates/agents/rules/` and `.agents/rules/`, **When** inspected, **Then** every rule includes valid Antigravity YAML frontmatter (`description` and `trigger: always_on` or `trigger: glob` with `globs`), and `harness-core.md` documents `buddhi_graph` alongside `buddhi_search`, `buddhi_read`, and `buddhi_memory`.
2. **Given** specialist subagents in `.agents/agents/*.md` (`backend-specialist`, `frontend-specialist`, `database-specialist`, `testing-specialist`, `security-specialist`, `deployment-specialist`, `git-specialist`), **When** inspected, **Then** their frontmatter and prompts properly equip them to use `buddhi_search`, `buddhi_read`, `buddhi_graph` (including `blast_radius`), and `buddhi_memory`.
3. **Given** `.agents/hooks.json`, **When** `SessionStart` or `PreToolUse` fires, **Then**:
   - On `SessionStart`: the hook checks `tree-graph.db` `built_at_commit` vs `git rev-parse HEAD` and OKF memory staleness in `<100ms` (fail-open, exit 0) and outputs `{"additionalContext": "..."}` if stale.
   - On `PreToolUse` (for file-read/grep tools targeting a workspace file): `guard_destructive.py` continues protecting against destructive shell commands, and `graph_context.py` queries `tree-graph.db` + `.agents/memory/` in `<50ms` (fail-open, `decision: "allow"`) to inject a concise `additionalContext` summary (`[Buddhi Graph] Symbols, community label/cohesion, caller/callee counts, and active path-scoped OKF memories`).
4. **Given** the completed implementation, **When** `ACKNOWLEDGMENTS.md`, `CHANGELOG.md`, and `README.md` are inspected, **Then** `ACKNOWLEDGMENTS.md` credits `Graphify` (`https://github.com/Graphify-Labs/graphify`, Safi Shamsi, Apache-2.0 / MIT with NOTICE and license texts), `CHANGELOG.md` documents all new features under `## [Unreleased]`, `README.md` documents `buddhi graph` and `buddhi_graph`, and `git status` confirms zero staged/committed files from `./temp/`.

---

### Edge Cases

- **Missing or Empty Code Graph (`tree-graph.db` absent)**: `buddhi_graph`, `buddhi_search`, SDD commands, and Antigravity hooks MUST degrade gracefully (returning a clear hint to run `buddhi generate` or exiting `0` with `{}` in hooks) without crashing or blocking the agent.
- **Super-Hub Nodes in Large Repos**: Utility functions/classes or loggers called from hundreds of places MUST NOT cause `buddhi_search` or `blast_radius` to pull the entire repository into a 2-hop neighborhood; traversal through nodes with `degree > max(50, p99_degree)` is blocked during transit hops while still reporting the super-hub itself as an impacted hub.
- **Ambiguous Symbol Names across Files**: When `shortest_path`, `blast_radius`, or `buddhi_graph` receives a bare symbol name (e.g., `run` or `Config`) that exists in multiple files, the tool MUST return a structured disambiguation list (`path/to/file.py::Symbol`) or score by file context rather than arbitrarily picking one or failing silently.
- **Circular Imports & Self-Loops**: `find_import_cycles`, `blast_radius`, and `shortest_path` MUST bound cycle enumeration (e.g., max 50 cycles) and track visited nodes so cyclic graphs never trigger infinite recursion.
- **Non-Git Workspaces or Detached HEAD**: When `git` is unavailable or the workspace has no commits, `built_at_commit` and `--git-ref` commands MUST fall back gracefully without raising unhandled `subprocess` errors.
- **Strict File-Size Ratchet (`<= 8,000 tokens` / `32 KB`)**: All new and modified Python source files under `src/buddhi/` MUST remain strictly below the `buddhi scripts check-file-size` budget by splitting logic cleanly across cohesive modules.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Cross-File Call & Inheritance Resolution)**: `src/buddhi/graph/` MUST build a project-wide `SymbolIndex` during resolution to resolve cross-file function/method calls (via resolved module/symbol imports and unique project symbols) and class/interface/trait inheritance (`INHERITS` edges) across supported languages.
- **FR-002 (Edge Provenance Confidence & Context)**: Graph edges in `CodeGraph` and SQLite `tree-graph.db` (`edges` table) MUST store `confidence` (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`), numeric `confidence_score` (`0.1–1.0`), and `context` (`call`, `import`, `inherit`, `type_ref`, `contains`).
- **FR-003 (Deterministic Leiden Clustering, Cohesion & Hub Naming)**: `src/buddhi/graph/clustering.py` MUST sort edges canonically before Leiden clustering, exclude super-hubs (`degree > max(50, p99_degree)`) during initial partitioning with neighbor-majority reattachment, sub-split oversized (`>25%` of clusterable nodes, min 10) or low-cohesion (`cohesion < 0.05`, min 50) communities, compute per-community `cohesion` (`actual_edges / max_possible_edges`), assign a deterministic hub-based `label`, and persist a `communities` table in `tree-graph.db`.
- **FR-004 (Incremental SHA-256 AST Cache & Git Commit Stamp)**: `buddhi generate` MUST cache per-file `FileExtraction` results keyed by `(file_path, sha256)` so unchanged files skip tree-sitter re-parsing on incremental runs, and record `built_at_commit` (current git `HEAD` SHA) in the SQLite `meta` table.
- **FR-005 (Topological Analysis & Blast Radius Engine)**: `src/buddhi/graph/analyze.py` MUST implement clean-room native algorithms on `tree-graph.db` for:
  1. `blast_radius`: given target files, symbols, or a `git diff` (`working`, `staged`, or `--git-ref`), computes direct and transitive callers/dependents, impacted Leiden communities (with cohesion), impacted `god_nodes`, crossed community bridges, newly introduced import cycles, and an overall risk classification (`low`, `medium`, `high`, `critical`).
  2. `god_nodes`: highest-degree symbol hubs excluding `directory`/`file` containers and builtin/type noise.
  3. `surprising_connections`: composite surprise scoring across confidence tiers, cross-directory hops, cross-community bridges, and peripheral-to-hub links.
  4. `suggest_questions`: diagnostic architecture review prompts across `ambiguous_edge`, `bridge_node`, `verify_inferred`, `isolated_nodes`, and `low_cohesion`.
  5. `shortest_path`: shortest relational path between two symbols with tiered symbol disambiguation.
  6. `find_import_cycles`: bounded file-level circular `IMPORTS` detection.
  7. `get_community` & `graph_stats`: community inspection and graph health/staleness summary.
- **FR-006 (Unified `buddhi_graph` MCP Tool & `buddhi graph` CLI)**:
  - Register `buddhi_graph` on the `buddhi-mcp` FastMCP server (`src/buddhi/mcp/server.py`) supporting `action` in `{"blast_radius", "god_nodes", "surprises", "questions", "shortest_path", "cycles", "community", "stats"}`.
  - Add `buddhi graph` Typer CLI command group (`src/buddhi/commands/graph_cmd.py` registered in `src/buddhi/cli.py`) exposing `blast-radius`, `analyze`, `path`, `cycles`, `community`, and `stats` with `--json` support.
- **FR-007 (IDF Scoring & Hub-Blocked BFS in `buddhi_search`)**: Upgrade `src/buddhi/mcp/tools/search.py` to rank lexical anchors with IDF-weighted multi-field scoring and squared term coverage `(matched_terms / total_terms)^2`, and replace unbounded `WHERE community_id IN (...)` community fetching with Hub-Blocked 2-Hop BFS + proximity-ranked community peers.
- **FR-008 (SDD Workflow Integration)**:
  - Update `buddhi sdd setup-plan` (and add `buddhi sdd impact`) to compute a Topological & Blast Radius Context Summary from `tree-graph.db`.
  - Update SDD skill templates (`src/buddhi/templates/agents/skills/{specify,explore-unknowns,spec-plan,spec-tasks,implement,verify,close-spec,ask,debug,status}/SKILL.md`) and active `.agents/skills/` counterparts to use `buddhi_graph` and `buddhi graph blast-radius` while keeping codebase documentation strictly in the existing OKF v0.2 `.buddhi/docs/` format.
- **FR-009 (Antigravity Customizations Compliance — Skills, Rules, Subagents, Hooks)**:
  - **Rules**: Add official Antigravity YAML frontmatter (`description`, `trigger: always_on` or `trigger: glob` with `globs`) to all rule files in `src/buddhi/templates/agents/rules/*.md` and `.agents/rules/*.md`, and document `buddhi_graph` in `harness-core.md`.
  - **Subagents**: Update specialist subagent definitions in `src/buddhi/templates/agents/agents/*.md` and `.agents/agents/*.md` so their `tools` frontmatter and instructions include `buddhi` MCP tools (`buddhi_search`, `buddhi_read`, `buddhi_graph`, `buddhi_memory`).
  - **Hooks**: Add a non-blocking, fail-open hook script (`graph_context.py`) registered in `.agents/hooks.json` (and template `src/buddhi/templates/agents/hooks.json`) for `SessionStart` (staleness check for `tree-graph.db` `built_at_commit` and OKF memory) and `PreToolUse` (injecting compact file symbol/community/caller/memory context via `additionalContext` in `<50ms`).
- **FR-010 (Attribution, Changelog, README & Temp Directory Protection)**:
  - Update `ACKNOWLEDGMENTS.md` with a dedicated `Graphify` section (`https://github.com/Graphify-Labs/graphify`, Author: Safi Shamsi, Apache-2.0 / MIT license and NOTICE attribution).
  - Update `CHANGELOG.md` under `## [Unreleased]` detailing the code graph, Blast Radius, SDD, MCP, CLI, and Antigravity hook/rule/subagent/skill enhancements.
  - Update `README.md` to document the new `buddhi graph` CLI commands, `buddhi_graph` MCP tool, and Blast Radius / SDD integration.
  - Never stage or commit any file from `./temp/`.

---

### Key Entities

- **`GraphEdge` (Extended)**: Represents a directed relationship (`CONTAINS`, `IMPORTS`, `CALLS`, `INHERITS`) between two `GraphNode`s, enriched with `confidence` (`EXTRACTED | INFERRED | AMBIGUOUS`), `confidence_score` (`float`), and `context` (`call | import | inherit | type_ref | contains`).
- **`CommunityInfo`**: Represents a detected Leiden community persisted in `tree-graph.db` (`communities` table) with `id` (`int`), `label` (`str`, named after highest-degree symbol hub), `node_count` (`int`), `cohesion` (`float`), `hub_node_id` (`str`), and `top_files` (`JSON list[str]`).
- **`BlastRadiusReport`**: Structured impact assessment for a set of changed files, symbols, or a `git diff`, containing `changed_nodes`, `direct_callers`, `transitive_callers`, `affected_communities`, `impacted_god_nodes`, `crossed_bridges`, `new_import_cycles`, and `risk_level`.
- **`TopologicalSummary`**: Combined diagnostic snapshot produced by `analyze.py` containing `god_nodes`, `surprising_connections`, `suggest_questions`, `import_cycles`, and `graph_stats`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Cross-File & Inheritance Resolution)**: On multi-file test suites across supported languages, cross-file calls to imported project symbols and class inheritance relationships resolve to internal `GraphNode` IDs (`resolved = 1`) with `>= 90%` accuracy on explicit module imports, and `INHERITS` edges are persisted in `tree-graph.db`.
- **SC-002 (Deterministic & Cohesive Communities)**: Running `buddhi generate` twice on the same repository under different `PYTHONHASHSEED` values produces 100% identical `community_id` assignments, community `label`s, and `cohesion` scores.
- **SC-003 (Incremental Rebuild Speed)**: Re-running `buddhi generate` when zero files have changed reuses the SHA-256 AST extraction cache for 100% of previously parsed files and records `built_at_commit` in `tree-graph.db`.
- **SC-004 (Token-Bounded Search & Sub-100ms Hooks)**: `buddhi_search` never exceeds `token_budget * 4` characters even when matching a symbol inside a 500+ node community, and `.agents/hooks/graph_context.py` completes `PreToolUse` context lookup in `< 100ms` while always exiting `0` (fail-open).
- **SC-005 (Quality Gates & Ratchet Compliance)**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/ tests/`, and `uv run buddhi scripts check-file-size --all` all pass with exit code `0`, and `git status` shows zero staged files from `./temp/`.

---

## Assumptions

- Existing OKF v0.2 documentation generation (`.buddhi/docs/`, `/document-codebase`, `buddhi docs plan`) remains the single source of truth for codebase concept documentation; `graphify`'s separate markdown wiki and `GRAPH_REPORT.md` are intentionally omitted in favor of `buddhi_graph` / `buddhi graph` and OKF docs.
- Multi-modal extractors from `graphify` (Whisper audio/video transcription, PDF/paper OCR, image vision LLM extraction) are out of scope so `buddhi-cli` remains a fast, deterministic CLI without heavy ML runtime dependencies.
- All new functionality is implemented as clean-room Python 3.10+ code native to `buddhi-cli`'s existing `tree-sitter`, `igraph`, `sqlite3`, `FastMCP`, and `Typer` stack.
