# Feature Specification: OKF & Claude Code Memory Layer for Antigravity Harness

**Feature Branch**: `005-okf-claude-memory-layer`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Analyze the current project where how the Antigravity agent harness memory is implemented, which is a very simple implementation. I want a more sophisticated memory implementation getting inspiration from Claude Code Memory standards and combining it with Google Open Knowledge Format. This way Antigravity will have proper memory layer per project. Note: The memory implementation should be well integrated with the existing Spec Driven Development workflow. 1. Use following references and additional online references, and do a proper research and provide a full spec for implementation. - Claude Code Memory: `https://code.claude.com/docs/en/memory` - Google Open Knowledge Format: `https://github.com/GoogleCloudPlatform/open-knowledge-format` 2. Update the Changelog under [Unreleased] this feature implementation 3. Update `ACKNOWLEDGMENTS.md` with proper references. 4. Update README accordingly."

---

## Executive Research Summary & Gap Analysis

### 1. Current `buddhi-cli` Memory Implementation (Gap Analysis)
- **Current State**: `buddhi init` scaffolds `.agents/memory/MEMORY.md` alongside four plain, unformatted Markdown topic files (`user-preferences.md`, `project-conventions.md`, `tech-decisions.md`, `feedback-history.md`). Entries are appended one per line by `/remember` with a `<150 char` pointer added to `MEMORY.md` (soft-capped at ~200 lines).
- **Identified Gaps**:
  1. **Zero OKF Alignment**: While `.buddhi/docs/` uses Google Open Knowledge Format (OKF v0.2) with YAML frontmatter, `sources[].content_hash` staleness tracking, `index.md`, and `log.md`, `.agents/memory/` is a flat list with no YAML frontmatter, no stable concept IDs, no source hash verification, no semantic relations, and no confidence/lifecycle status.
  2. **Missing Claude Code Memory Mechanics**: No hierarchical scope separation (project git-tracked vs. local gitignored `.agents/memory.local/` vs. user global `~/.buddhi/memory/`), no path-scoped glob filtering (`paths: ["src/api/**/*.py"]`) for just-in-time rule/memory loading, no `@path/to/file` inline reference expansion (up to 5 hops), and no subagent-scoped persistent memory (`memory: project | local | user` in `.agents/agents/<specialist>.md`).
  3. **No Deterministic Tooling**: No `buddhi memory` CLI or `buddhi_memory` MCP tool exists to deterministically validate the 200-line / 25KB `MEMORY.md` entrypoint budget, detect stale memories when referenced source code changes (`content_hash` mismatch), auto-rebuild `MEMORY.md` / `<topic>/index.md`, or migrate legacy flat files.
  4. **Shallow SDD Integration**: While `harness-core.md` mentions memory, the SDD skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`, `/close-spec`) do not systematically query domain/path-scoped memories before planning or promote verified architectural choices (`choices.md`) and closed specs into durable OKF memory nodes.

### 2. Claude Code Memory Standards (`https://code.claude.com/docs/en/memory`)
- **Strict Entrypoint Cap**: `MEMORY.md` acts as the always-loaded index entrypoint, strictly bounded at **200 lines / 25 KB** so context windows never bloat. Detailed notes live in separate topic files read on-demand.
- **Scoped Memory Hierarchy**:
  - **Project Memory** (`.agents/memory/`): Shared, git-tracked project knowledge.
  - **Local Memory** (`.agents/memory.local/`): Personal/machine-specific project overrides, automatically gitignored.
  - **User Memory** (`~/.buddhi/memory/`): Cross-project user preferences and global workflow habits.
- **Path-Scoped Activation (`paths` frontmatter)**: Memory and rule nodes can declare glob patterns (`paths: ["src/mcp/**/*.py", "tests/**"]`) so agents load only memories matching the active files/directories being inspected or modified.
- **`@path` Imports**: Memory files can reference external or sibling files via `@path/to/file` syntax, resolved inline up to a maximum recursion depth of **5 hops** with circular-reference protection.
- **Subagent Persistent Memory**: Domain specialists (`backend-specialist`, `frontend-specialist`, `database-specialist`, `testing-specialist`, `security-specialist`, `deployment-specialist`, `git-specialist`) declare `memory: project | local | user` in their agent frontmatter and curate domain-specific insights under `.agents/agent-memory/<agent-name>/MEMORY.md`.
- **Interactive Management (`/memory` & `/remember`)**: Dedicated commands to inspect active memory scopes, check budget utilization, audit stale nodes, compact oversized indexes, and capture new knowledge.

### 3. Google Open Knowledge Format (`https://github.com/GoogleCloudPlatform/open-knowledge-format`)
- **OKF v0.2 Bundle Architecture**:
  - Root index (`MEMORY.md` / `index.md`) carries `okf_version: "0.2"` frontmatter.
  - Subdirectory `index.md` files (`decisions/index.md`, `conventions/index.md`, `preferences/index.md`, `feedback/index.md`, `sdd/index.md`) list concept nodes as `* [Title](relative/path.md) - summary` without frontmatter.
  - Chronological `log.md` records memory mutations (`create`, `update`, `supersede`, `archive`, `migrate`) newest-first.
- **OKF Concept Node Schema**:
  Each memory item is an atomic Markdown file (`<topic>/<slug>.md`) with structured YAML frontmatter:
  ```yaml
  ---
  id: mem-decision-sqlite-wal
  kind: decision              # decision | convention | preference | feedback | sdd-rationale | domain-learning
  title: Use SQLite WAL Mode for Graph Persistence
  summary: Enable WAL journal mode on tree-graph.db to support concurrent MCP reads during generation.
  status: stable              # draft | stable | deprecated | superseded
  confidence: verified        # verified | inferred | proposed
  scope: project              # project | local | user | agent:<name>
  paths:
    - "src/buddhi/persist/**/*.py"
    - "src/buddhi/mcp/**/*.py"
  tags: [sqlite, concurrency, mcp]
  generated:
    by: antigravity/claude-opus-4-7
    at: "2026-10-26T13:20:00Z"
  sources:
    - id: src-sqlite-writer
      resource: "src/buddhi/persist/sqlite_writer.py#L15-L48"
      content_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  relations:
    - kind: supersedes
      target: mem-decision-sqlite-default
    - kind: derived_from_spec
      target: ".buddhi/specs/done/005-okf-claude-memory-layer/spec.md"
  ---
  ```
  *(Note: Per `.agents/rules/okf-docs.md`, OKF Attested Computation fields `runtime`, `parameters`, `executor`, `attester` are strictly omitted.)*

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hybrid OKF Memory Bundle, CLI Engine & Legacy Migration (Priority: P1)

As a developer using `buddhi-cli`, I want `buddhi init` and a new `buddhi memory` CLI command group to scaffold, manage, validate, and migrate an OKF v0.2 + Claude Code-compliant memory bundle under `.agents/memory/`, so that project knowledge is stored as structured, provenance-tracked OKF concept nodes indexed by a budget-enforced `MEMORY.md` entrypoint.

**Why this priority**: This is the foundational data model, storage engine, and CLI layer (`P1` MVP). Every MCP tool, SDD workflow integration, and subagent memory feature depends on the OKF memory schema, index generator, staleness detector, and legacy migration engine.

**Independent Test**: Can be fully tested by running `uv run buddhi init` on a fresh or existing repository (containing legacy `user-preferences.md`, `project-conventions.md`, `tech-decisions.md`, `feedback-history.md`), then running `uv run buddhi memory add`, `uv run buddhi memory status`, `uv run buddhi memory validate`, `uv run buddhi memory search`, and `uv run buddhi memory sync` and verifying the resulting `.agents/memory/` files, SHA-256 content hashes, `MEMORY.md` 200-line/25KB enforcement, and exit codes.

**Acceptance Scenarios**:

1. **Given** a project initialized with `buddhi init`, **When** `.agents/memory/` is scaffolded, **Then** it contains `MEMORY.md` (with `okf_version: "0.2"` frontmatter and `<150 char` pointer lines), `log.md`, topic subdirectories (`decisions/`, `conventions/`, `preferences/`, `feedback/`, `sdd/`) each with an `index.md`, and `.gitignore` rules ignoring `.agents/memory.local/` and `.agents/agent-memory-local/`.
2. **Given** an existing project with non-empty legacy flat files (`.agents/memory/user-preferences.md`, `project-conventions.md`, `tech-decisions.md`, `feedback-history.md`), **When** `buddhi init` or `buddhi memory migrate` runs, **Then** each bullet/line entry in the legacy files is non-destructively converted into an OKF concept file under the corresponding topic directory (`preferences/`, `conventions/`, `decisions/`, `feedback/`), legacy files are backed up as `.md.bak`, and `MEMORY.md` + `log.md` are updated.
3. **Given** a developer or agent runs `buddhi memory add --kind decision --title "..." --summary "..." --body "..." [--path-glob "src/mcp/**"] [--source "src/buddhi/mcp/server.py#L1-L40"] [--scope project|local|user|agent:<name>]`, **When** the command executes, **Then** it computes the SHA-256 `content_hash` of the cited source file/line-range, writes the atomic OKF `.md` concept file, updates `<topic>/index.md` and `MEMORY.md`, and records a timestamped entry in `.agents/memory/log.md`.
4. **Given** a source file cited in a memory node's `sources[0].resource` is modified, **When** `buddhi memory status` or `buddhi memory validate` runs, **Then** the memory node is flagged as `stale: true` (hash mismatch) so the agent or user knows to verify or refresh that decision/convention.
5. **Given** `MEMORY.md` exceeds 180 lines (warning threshold) or 200 lines / 25 KB (hard cap), **When** `buddhi memory validate` or `buddhi memory compact` runs, **Then** it reports the budget violation and `compact` prunes/summarizes lower-priority or superseded (`status: deprecated | superseded`) pointers out of the top-level `MEMORY.md` while keeping them searchable in `<topic>/index.md`.

---

### User Story 2 - `buddhi_memory` MCP Tool, Path-Scoped Filtering & `@path` Expansion (Priority: P2)

As an AI coding agent working in Antigravity, I want a dedicated `buddhi_memory` tool on the `buddhi-mcp` server that supports querying memories by natural language, topic, scope, or active file paths (`paths` glob matching), reading memory nodes with `@path` import expansion (up to 5 hops), and writing new OKF memory nodes, so that I can retrieve high-signal, non-stale project context without context bloat.

**Why this priority**: Agents interact with the workspace primarily through MCP tools during coding, planning, and debugging. Exposing deterministic memory retrieval and path-scoped filtering via `buddhi-mcp` makes the memory layer instantaneously accessible to the main agent and all specialist subagents.

**Independent Test**: Can be independently tested via pytest unit/integration tests calling `buddhi_memory(action="search" | "read" | "remember" | "status", ...)` on `buddhi-mcp` and verifying path-glob filtering, `@path` recursion up to 5 hops with cycle detection, staleness warnings in tool output, and atomic OKF writes.

**Acceptance Scenarios**:

1. **Given** OKF memory nodes exist with `paths: ["src/buddhi/mcp/**/*.py"]` and `paths: ["src/buddhi/graph/**/*.py"]`, **When** an agent calls `buddhi_memory(action="search", active_files=["src/buddhi/mcp/server.py"])`, **Then** global memories (no `paths` restriction) and memories matching `src/buddhi/mcp/**/*.py` are returned, while unrelated path-scoped memories are excluded.
2. **Given** a memory concept file contains `@.buddhi/specs/done/001-feature/spec.md` or `@.agents/memory/decisions/mem-other.md`, **When** `buddhi_memory(action="read", id="...")` is called with `expand_imports=True`, **Then** `@path` references are resolved inline up to a maximum depth of 5 hops, and any circular `@path` loop is safely halted with a clear cycle marker.
3. **Given** an agent discovers a convention or architectural decision during a session, **When** it calls `buddhi_memory(action="remember", kind="convention", title="...", summary="...", content="...", paths=[...], sources=[...])`, **Then** the MCP tool writes the validated OKF concept node, computes source SHA-256 hashes, updates `MEMORY.md` and `log.md`, and returns the created concept `id` and path.

---

### User Story 3 - End-to-End SDD Lifecycle & Subagent Memory Integration (Priority: P2)

As a developer running the Spec-Driven Development (SDD) workflow (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`, `/close-spec`) and memory skills (`/remember`, `/memory`, `/status`), I want every SDD stage and domain specialist subagent to automatically consult relevant OKF memories and promote verified architectural decisions into durable project or specialist memory.

**Why this priority**: The user explicitly required that the memory implementation be well integrated with the existing Spec-Driven Development workflow and specialist subagents.

**Independent Test**: Can be tested by inspecting the updated SDD skills, specialist agent definitions (`.agents/agents/*.md`), and harness rules (`.agents/rules/harness-core.md`, `.agents/rules/okf-docs.md`), and running `buddhi memory sdd-promote` on a sample `.buddhi/specs/<branch>/` directory containing `plan.md`, `choices.md`, and `spec.md` to verify automatic extraction of `sdd-rationale` and `decision` OKF memory nodes.

**Acceptance Scenarios**:

1. **Given** an active SDD cycle, **When** `/specify` or `/spec-plan` runs, **Then** the agent queries `buddhi_memory` (or `buddhi memory search`) for prior `decision`, `convention`, `preference`, and `sdd-rationale` nodes matching the feature domain and target file paths before asking clarifying questions or synthesizing `plan.md`.
2. **Given** `/spec-plan` dispatches specialist subagents (`backend-specialist`, `frontend-specialist`, `database-specialist`, `testing-specialist`, `security-specialist`, `deployment-specialist`, `git-specialist`), **When** a specialist runs, **Then** its `.agents/agents/<specialist>.md` definition declares `memory: project` and instructs the specialist to consult `.agents/agent-memory/<specialist>/MEMORY.md` alongside project memory.
3. **Given** `/implement` records unprompted architectural choices in `.buddhi/specs/<branch>/choices.md` (classified as `sound`) or `/verify` + `/close-spec` archives a shipped feature to `.buddhi/specs/done/<branch>/`, **When** `buddhi memory sdd-promote --branch <branch>` (or `/close-spec`) runs, **Then** verified decisions, invariants, and sound choices are promoted into `.agents/memory/sdd/` and `.agents/memory/decisions/` with `relations: [{ kind: derived_from_spec, target: ".buddhi/specs/done/<branch>/spec.md" }]` and source code `content_hash` anchors.
4. **Given** a user invokes `/memory` or `/remember` or `/status`, **When** the skill runs, **Then** `/remember` captures OKF-formatted memory nodes via `buddhi memory add` / `buddhi_memory`, `/memory` provides full interactive inspection/compaction/staleness auditing of all memory scopes (`project`, `local`, `user`, `agent`), and `/status` reports `MEMORY.md` line/byte budget usage, concept counts by kind, and stale memory node counts.

---

### User Story 4 - Documentation, Changelog & Acknowledgments Updates (Priority: P3)

As a maintainer and user of `buddhi-cli`, I want `CHANGELOG.md` (under `[Unreleased]`), `ACKNOWLEDGMENTS.md`, and `README.md` thoroughly updated to document the OKF + Claude Code memory architecture, CLI commands, MCP tool, SDD memory lifecycle, and upstream attributions.

**Why this priority**: Explicitly requested deliverables (Items 2, 3, and 4 in the user prompt) ensuring the project documentation and open-source attributions accurately reflect the new architecture once implemented.

**Independent Test**: Can be verified by checking `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, and `README.md` for complete, accurate documentation of `buddhi memory`, `buddhi_memory`, `/memory`, `/remember`, SDD memory integration, and formal attribution sections for Anthropic's Claude Code Memory documentation and Google Cloud Platform's Open Knowledge Format (OKF).

**Acceptance Scenarios**:

1. **Given** the feature implementation is completed, **When** `CHANGELOG.md` is inspected under `## [Unreleased]`, **Then** it includes a comprehensive entry detailing the OKF + Claude Code Memory Layer, `buddhi memory` CLI subcommands, `buddhi_memory` MCP tool, subagent memory scopes, legacy migration, and SDD lifecycle integration.
2. **Given** `ACKNOWLEDGMENTS.md` is inspected, **Then** it includes structured attribution sections referencing **Claude Code Memory** (`https://code.claude.com/docs/en/memory`) and **Google Open Knowledge Format (OKF)** (`https://github.com/GoogleCloudPlatform/open-knowledge-format`, Apache-2.0 License) alongside existing attributions.
3. **Given** `README.md` is inspected, **Then** it documents the `buddhi memory` CLI command group, the `buddhi_memory` MCP tool, the `.agents/memory/` OKF bundle structure, the `/memory` and enhanced `/remember` skills, SDD memory integration, and updated Acknowledgments links.

---

### Edge Cases

- **Legacy Memory Migration Idempotency**: What happens when `buddhi init` is run multiple times on a repo that had legacy `user-preferences.md`? Migration only converts legacy files when `.md` legacy files contain actual user entries (not just the default "No entries yet." placeholder) and have not already been migrated; migrated files are renamed to `.md.bak` so re-runs never duplicate nodes.
- **Entrypoint Cap Overflow (`>200 lines` or `>25 KB`)**: What happens when adding a new memory node would push `.agents/memory/MEMORY.md` past 200 lines or 25,600 bytes? `buddhi memory add` / `sync` automatically keeps `MEMORY.md` within the 200-line / 25KB hard cap by prioritizing active `verified`/`stable` nodes and moving older or `inferred`/`superseded` pointers to `<topic>/index.md`, emitting a clear notice.
- **Circular `@path` Imports**: What happens if `mem-a.md` imports `@.agents/memory/decisions/mem-b.md` which imports `@.agents/memory/decisions/mem-a.md`? The `@path` resolver tracks visited canonical paths per expansion branch and stops at depth 5 or on cycle detection, inserting `<!-- @import-cycle-detected: <path> -->`.
- **Path Traversal in `@path` Imports**: What happens if a memory file contains `@../../../../etc/passwd`? `@path` resolution is strictly sandboxed to the workspace root directory and `~/.buddhi/memory/`; paths resolving outside those roots are rejected.
- **Missing or Deleted Source Files in `sources`**: What happens when `sources[0].resource` points to a file or line range that was deleted or refactored? `buddhi memory validate` and `buddhi memory status` mark the node `stale: true` with `reason: "source_missing"` rather than crashing.
- **Missing OKF Frontmatter in Hand-Edited Memory Files**: If a user manually drops a `.md` file into `.agents/memory/decisions/` without YAML frontmatter, `buddhi memory validate` reports a clear validation warning and `buddhi memory sync --fix` can scaffold default OKF v0.2 frontmatter around the prose.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (OKF v0.2 Memory Bundle Layout)**: `buddhi init` MUST scaffold `.agents/memory/` as an OKF v0.2 bundle containing:
  - `.agents/memory/MEMORY.md` (root entrypoint index with `okf_version: "0.2"` YAML frontmatter, capped at 200 lines and 25 KB).
  - `.agents/memory/log.md` (chronological mutation log, newest first, no frontmatter).
  - Topic directories `.agents/memory/decisions/`, `.agents/memory/conventions/`, `.agents/memory/preferences/`, `.agents/memory/feedback/`, and `.agents/memory/sdd/`, each with an OKF `index.md` (no frontmatter).
- **FR-002 (Multi-Scope Memory Hierarchy)**: The memory layer MUST support four scopes inspired by Claude Code Memory:
  - `project`: `.agents/memory/` (git-tracked, shared team/project knowledge).
  - `local`: `.agents/memory.local/` (gitignored, personal project-local overrides).
  - `user`: `~/.buddhi/memory/` (cross-project user preferences).
  - `agent:<name>`: `.agents/agent-memory/<name>/` (git-tracked specialist subagent memory) and `.agents/agent-memory-local/<name>/` (gitignored local subagent memory).
- **FR-003 (OKF Concept Node Schema)**: Each memory concept file MUST use YAML frontmatter with `id`, `kind` (`decision` | `convention` | `preference` | `feedback` | `sdd-rationale` | `domain-learning`), `title`, `summary`, `status` (`draft` | `stable` | `deprecated` | `superseded`), `confidence` (`verified` | `inferred` | `proposed`), `scope`, optional `paths` (list of glob strings), `tags`, `generated` (`{by, at}`), optional `sources` (`[{id, resource, content_hash}]`), and optional `relations` (`[{kind, target}]`). It MUST NOT include OKF Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`).
- **FR-004 (Source Provenance & Staleness Detection)**: When a memory concept cites one or more workspace files (`path/to/file.ext` or `path/to/file.ext#L10-L30`) in `sources`, the system MUST compute the SHA-256 `content_hash` of the referenced file or line slice and detect staleness whenever the current file content hash no longer matches `sources[].content_hash`.
- **FR-005 (Path-Scoped Glob Activation)**: Memory nodes and `.agents/rules/*.md` files supporting `paths: [...]` YAML frontmatter MUST be filterable by active workspace file paths using standard glob matching (`fnmatch` / `PurePosixPath` globbing) so agents load only relevant domain memories for the files being read or edited.
- **FR-006 (`@path` Import Expansion)**: Memory reading tools MUST support `@path/to/file` inline imports up to a maximum recursion depth of 5 hops, with cycle detection and workspace/user-memory path sandboxing.
- **FR-007 (Automatic Legacy Migration)**: `buddhi init` and `buddhi memory migrate` MUST detect legacy `.agents/memory/{user-preferences,project-conventions,tech-decisions,feedback-history}.md` files, convert any non-placeholder entries into OKF concept nodes in their corresponding topic subdirectories, archive legacy files as `.md.bak` (or remove unchanged boilerplate templates), and rebuild `MEMORY.md` and `log.md`.
- **FR-008 (`buddhi memory` CLI Command Group)**: `buddhi` MUST expose a `buddhi memory` Typer CLI command group with subcommands:
  - `buddhi memory status [--json]`: Report entrypoint line/KB usage vs. 200-line/25KB cap, counts by topic/scope/status, and stale node count.
  - `buddhi memory add`: Deterministically create or update an OKF memory concept node, compute `sources` SHA-256 hashes, sync indexes, and append to `log.md`.
  - `buddhi memory search <query> [--kind ...] [--scope ...] [--active-file ...] [--json]`: Search memory nodes across scopes with lexical scoring, tag matching, and `paths` glob filtering.
  - `buddhi memory read <id_or_path> [--expand-imports]`: Read a memory concept node with optional `@path` expansion (max 5 hops).
  - `buddhi memory validate [--json]`: Verify OKF frontmatter compliance, `MEMORY.md` 200-line/25KB caps, broken `relations`, and stale `sources[].content_hash` references.
  - `buddhi memory sync`: Reconcile all `<topic>/index.md` files and `.agents/memory/MEMORY.md` from the concept files on disk.
  - `buddhi memory compact`: Enforce the 200-line / 25KB cap on `MEMORY.md` by demoting `superseded`/`deprecated` or oldest `inferred` pointers from the root index while keeping them in `<topic>/index.md`.
  - `buddhi memory migrate`: Explicitly run legacy flat-file migration.
  - `buddhi memory sdd-promote [--branch <branch>]`: Extract verified architectural decisions and `sound` choices from `.buddhi/specs/<branch>/` (or `.buddhi/specs/done/<branch>/`) into OKF memory nodes under `.agents/memory/sdd/` and `.agents/memory/decisions/`.
- **FR-009 (`buddhi_memory` MCP Tool)**: `buddhi-mcp` MUST expose a `buddhi_memory` tool supporting actions `search`, `read`, `remember`, `status`, and `promote_sdd`, enabling agents to query path-scoped memories, read nodes with `@path` expansion, and persist new OKF memories directly over MCP.
- **FR-010 (SDD Workflow Integration)**: All SDD skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`, `/close-spec`) MUST be updated so that:
  - `/specify` and `/spec-plan` query `buddhi_memory` for relevant domain/path memories and surface any stale memories affecting the feature area.
  - `/tasks` includes memory capture/verification tasks when architectural seams or conventions are introduced.
  - `/implement` consults path-scoped memories for files being modified and records unprompted choices in `choices.md`.
  - `/verify` validates that new architectural conventions or decisions introduced by the feature are captured and `buddhi memory validate` passes.
  - `/close-spec` runs `buddhi memory sdd-promote` to archive durable spec rationale and `sound` choices into `.agents/memory/sdd/` and repoints any spec relations to `.buddhi/specs/done/<branch>/`.
- **FR-011 (Skills & Subagent Frontmatter)**:
  - Add a new `/memory` skill (`.agents/skills/memory/SKILL.md`) for interactive memory management, inspection, staleness auditing, and compaction.
  - Upgrade `/remember` (`.agents/skills/remember/SKILL.md`) and `/status` (`.agents/skills/status/SKILL.md`) to use the OKF memory schema and `buddhi memory` / `buddhi_memory`.
  - Update specialist subagent templates (`.agents/agents/*.md`) with `memory: project` frontmatter and instructions to consult/update their subagent memory and project memory.
- **FR-012 (Documentation, Changelog & Acknowledgments)**:
  - Update `CHANGELOG.md` under `## [Unreleased]` with full release notes for the OKF + Claude Code Memory Layer.
  - Update `ACKNOWLEDGMENTS.md` with proper references and attributions for Claude Code Memory (`https://code.claude.com/docs/en/memory`) and Google Open Knowledge Format (`https://github.com/GoogleCloudPlatform/open-knowledge-format`).
  - Update `README.md` to document `buddhi memory`, `buddhi_memory`, the OKF memory bundle architecture, `/memory`, `/remember`, and SDD integration.

### Key Entities

- **`MemoryNode`**: An individual OKF v0.2 concept file (`<topic>/<slug>.md`) with structured frontmatter (`id`, `kind`, `title`, `summary`, `status`, `confidence`, `scope`, `paths`, `tags`, `generated`, `sources`, `relations`) and Markdown body sections (`# Summary`, `# Context & Rationale`, `# Rules / Invariants`, `# References`).
- **`MemorySource`**: A provenance anchor (`id`, `resource`, `content_hash`) tying a `MemoryNode` to a specific workspace file and optional `#L<start>-L<end>` line range via SHA-256 hashing.
- **`MemoryRelation`**: A typed directed edge (`supersedes`, `depends_on`, `related_to`, `derived_from_spec`, `affects`) linking a `MemoryNode` to another memory ID, OKF code doc, or SDD specification.
- **`MemoryIndex`**: The root `.agents/memory/MEMORY.md` entrypoint (carrying `okf_version: "0.2"`, strictly capped at 200 lines and 25 KB, with `<150 char` pointer lines) and per-topic `<topic>/index.md` files.
- **`MemoryLog`**: The chronological `.agents/memory/log.md` audit trail recording memory creations, updates, compactions, SDD promotions, and migrations.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (Entrypoint Budget Guarantee)**: `.agents/memory/MEMORY.md` remains strictly `<= 200 lines` and `<= 25,600 bytes` (25 KB), with individual pointer lines `<= 150 characters`, enforced deterministically by `buddhi memory validate` and `buddhi memory compact`.
- **SC-002 (100% Legacy Migration Fidelity)**: Running `buddhi init` or `buddhi memory migrate` on a workspace with legacy flat memory files converts 100% of user entries into valid OKF v0.2 concept files without data loss and passes `buddhi memory validate` with zero errors.
- **SC-003 (Deterministic Staleness Detection)**: Modifying any line within a referenced `sources[].resource` (`file.py#L10-L25`) causes `buddhi memory validate` and `buddhi memory status` to deterministically report the affected memory node as stale (`stale: true`) in under 100ms for a 100-node memory bundle.
- **SC-004 (Path-Scoped Precision & `@path` Safety)**: `buddhi_memory(action="search", active_files=[...])` returns 100% of matching path-scoped and global memories while filtering out non-matching path-scoped memories, and `buddhi_memory(action="read", expand_imports=True)` resolves nested `@path` imports up to 5 hops while blocking cycles and out-of-workspace path traversal in 100% of test cases.
- **SC-005 (Quality Gates & Documentation Completeness)**: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src/ tests/` all exit with code `0`, and `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, and `README.md` contain complete, accurate documentation and references.

---

## Assumptions

- Python `>= 3.10` standard library (`hashlib`, `pathlib`, `fnmatch`, `re`, `json`, `datetime`) plus existing project dependencies (`typer`, `rich`, `mcp`) are sufficient; no heavy external vector database or embedding model dependency is required so `buddhi-cli` remains fast, offline-capable, and deterministic.
- Both `.agents/` in the `buddhi-cli` repo dogfooding directory and `src/buddhi/templates/agents/` (the package templates synced by `buddhi init`) will be kept in sync so that `buddhi-cli` dogfoods the new memory layer itself and scaffolds it into user projects.
- Updates to `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, and `README.md` are specified as core deliverables in this spec (User Story 4, `FR-012`) and will be executed during the `/implement` phase alongside the code, skill, and template changes.
