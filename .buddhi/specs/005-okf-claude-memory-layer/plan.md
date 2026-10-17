# Implementation Plan: OKF & Claude Code Memory Layer

**Branch**: `005-okf-claude-memory-layer` | **Date**: 2026-10-26 | **Spec**: [.buddhi/specs/005-okf-claude-memory-layer/spec.md](file:///C:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/005-okf-claude-memory-layer/spec.md)

**Input**: Feature specification from `.buddhi/specs/005-okf-claude-memory-layer/spec.md`

## Summary

Implement a deterministic, project-scoped memory layer for Google Antigravity agent harnesses created by `buddhi-cli`, synthesizing the architectural best practices of **Claude Code Memory** (200-line / 25KB budget-enforced `MEMORY.md` index entrypoint, multi-scope hierarchy: `project` / `local` / `user` / `agent:<name>`, path-scoped glob matching, `@path` import expansion up to 5 hops, subagent persistent memory) and the **Google Open Knowledge Format (OKF v0.2)** (atomic concept nodes with YAML frontmatter, `sources[].content_hash` SHA-256 staleness tracking, directory `index.md` files, and chronological `log.md`).

The memory layer is exposed via:
1. Pure Python memory core under `src/buddhi/memory/` (models, frontmatter parser, provenance hasher, resolver, bundle store, legacy migrator, SDD promoter, security sandboxing).
2. Typer CLI commands under `buddhi memory` (`status`, `add`, `search`, `read`, `validate`, `sync`, `compact`, `migrate`, `sdd-promote`) wired to `src/buddhi/cli.py`.
3. FastMCP tool `buddhi_memory` added to `buddhi-mcp` (`search`, `read`, `remember`, `status`, `promote_sdd`).
4. End-to-end SDD lifecycle integration (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`, `/close-spec`), new `/memory` skill, upgraded `/remember` and `/status` skills, and subagent frontmatter declarations (`memory: project`).
5. Complete documentation updates across `CHANGELOG.md` [Unreleased], `ACKNOWLEDGMENTS.md`, and `README.md`.

---

## Technical Context

**Language/Version**: Python >= 3.10  
**Primary Dependencies**: `typer>=0.12.0`, `rich>=13.0.0`, `mcp>=1.0.0`, `pyyaml>=6.0` (standard library: `hashlib`, `pathlib`, `fnmatch`, `re`, `json`, `datetime`)  
**Storage**: Plain-text OKF v0.2 Markdown bundle under `.agents/memory/` (`MEMORY.md`, `log.md`, `decisions/`, `conventions/`, `preferences/`, `feedback/`, `sdd/`), gitignored `.agents/memory.local/`, `~/.buddhi/memory/`, and `.agents/agent-memory/<agent>/`  
**Testing**: `pytest` with Typer `CliRunner`, standard `tmp_path` fixture, and `FastMCP` integration suite  
**Target Platform**: Cross-platform (Windows, Linux, macOS) with normalized line endings (`\r\n` -> `\n`) for cross-platform SHA-256 hash parity  
**Project Type**: CLI / Developer Tooling / Agent Harness Generator  
**Performance Goals**: <100ms validation and search across a 100-node memory bundle  
**Constraints**: Zero network or heavy vector database dependencies; strict 200-line / 25,600-byte cap on `MEMORY.md`; strict max-5-hop recursion limit with circular import protection and workspace directory sandboxing on `@path` imports; strict rejection of OKF Attested Computation fields (`runtime`, `parameters`, `executor`, `attester`)  
**Scale/Scope**: Per-project memory with multi-project user defaults; seamless migration of legacy 4 flat topic files without data loss  

---

## AGENTS.md Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Project build & test commands adhered to (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/ tests/`)
- [x] Architectural constraints respected (no unapproved external dependencies; safe YAML parsing; no hand-editing OKF content hashes without updating files)
- [x] Antigravity harness conventions respected (skills in `.agents/skills/<name>/SKILL.md`, rules in `.agents/rules/`, memory in `.agents/memory/`, MCP in `buddhi-mcp`)
- [x] Mechanical hook compliance (no destructive commands without `CONFIRMED`)

---

## Architecture & Multi-Angle Lens Evaluation

### Lens 1: Fewest-Slices (Minimal viable change delivering value)
- **Slice 1 (Foundation)**: Core OKF data model (`models.py`, `frontmatter.py`), SHA-256 hasher (`hash.py`), and bundle store (`store.py`).
- **Slice 2 (Security & Resolution)**: Import resolver with 5-hop recursion cap, cycle guard, and path sandbox (`resolver.py`, `security.py`).
- **Slice 3 (Migration & CLI)**: Legacy migrator (`migrate.py`) and Typer commands (`commands/memory.py`).
- **Slice 4 (MCP & SDD Skills)**: `buddhi_memory` tool in `src/buddhi/mcp/tools/memory.py`, SDD promotion (`sdd_promote.py`), and updated agent skills (`/memory`, `/remember`, `/status`, `/spec-plan`, `/close-spec`).
- **Slice 5 (Closeout)**: `CHANGELOG.md`, `ACKNOWLEDGMENTS.md`, `README.md`.

### Lens 2: Risk-First (De-risking technical & security hazards early)
1. **Path Traversal via `@path`**: Invariant: Any `@path` import must resolve strictly within `workspace_root` or `~/.buddhi/memory/` using `Path.is_relative_to()`. UNC paths, Windows reserved device names, and unverified symlinks are rejected outright.
2. **Infinite Recursion / DoS**: Invariant: Recursion depth capped at 5; per-branch visited set tracking halts cycles with `<!-- @import-cycle-detected: <path> -->`; 100KB per-file cap and 256KB cumulative buffer cap.
3. **YAML Parsing Exploit**: Invariant: Strictly use `yaml.safe_load()`. Strip/reject OKF Attested Computation fields (`runtime`, `parameters`, etc.).
4. **Secret Leakage in Git-Tracked Memory**: Invariant: Regex scanner rejects API keys, private keys, and connection strings from being persisted to `scope: project`.
5. **Cross-Platform Hash Discrepancies**: Invariant: Normalize CRLF -> LF before SHA-256 hashing so hashes calculated on Windows match Linux CI.

### Lens 3: Seam-Quality (Decoupled boundaries & clean interfaces)
- `src/buddhi/memory/`: Completely self-contained engine. Does not import CLI or MCP modules.
- `src/buddhi/commands/memory.py`: Thin CLI controller delegating all mutations to `MemoryStore`.
- `src/buddhi/mcp/tools/memory.py`: Thin MCP wrapper exposing `execute_buddhi_memory()` to `FastMCP`.
- `src/buddhi/util/fsutil.py` & `src/buddhi/commands/init.py`: Single call site to `migrate_legacy_memory()` and `.gitignore` update.

---

## Project Structure

### Documentation & Specifications (this feature)
```text
.buddhi/specs/005-okf-claude-memory-layer/
├── spec.md              # Feature specification (completed)
└── plan.md              # This architecture plan
```

### Source Code Additions & Modifications
```text
src/buddhi/
├── memory/                           # [NEW] Pure Python OKF Memory Core
│   ├── __init__.py                   # Public exports
│   ├── models.py                     # OKF v0.2 data classes (MemoryNode, MemorySource, MemoryRelation, enums)
│   ├── frontmatter.py                # Safe YAML frontmatter serializer/parser
│   ├── hash.py                       # Resource anchor parsing, SHA-256 line-slicing & staleness detector
│   ├── security.py                   # Sandbox path validator, secret scanner, slug sanitization
│   ├── resolver.py                   # Glob pattern matcher (paths) & safe @path import recursion
│   ├── store.py                      # Multi-scope bundle store, MEMORY.md 200-line/25KB cap, log.md
│   ├── migrate.py                    # Legacy flat-file converter (.md -> OKF topic nodes + .md.bak)
│   └── sdd_promote.py                # SDD promotion (plan.md, choices.md, spec.md -> OKF nodes)
├── commands/
│   ├── memory.py                     # [NEW] Typer CLI command group `buddhi memory ...`
│   └── init.py                       # [MODIFIED] Wire legacy memory migration & bundle verification into init
├── mcp/
│   ├── server.py                     # [MODIFIED] Register `buddhi_memory` tool
│   └── tools/
│       └── memory.py                 # [NEW] MCP tool implementation (search, read, remember, status, promote_sdd)
├── util/
│   └── fsutil.py                     # [MODIFIED] Ensure .agents/memory.local/ and agent-memory-local/ in .gitignore
├── templates/agents/
│   ├── memory/                       # [UPDATED] OKF v0.2 templates (MEMORY.md, log.md, topic index.md files)
│   ├── agents/                       # [UPDATED] Subagent markdown templates with `memory: project`
│   └── skills/
│       ├── memory/SKILL.md           # [NEW] /memory skill for interactive inspection & compaction
│       ├── remember/SKILL.md         # [UPDATED] /remember skill using OKF schema & CLI/MCP
│       ├── status/SKILL.md           # [UPDATED] /status skill reporting memory budget & staleness
│       ├── spec-plan/SKILL.md        # [UPDATED] Grounding in OKF memory before planning
│       └── close-spec/SKILL.md       # [UPDATED] Promoting verified choices & rationale on spec close
├── cli.py                            # [MODIFIED] Mount `memory_app` on root Typer CLI
CHANGELOG.md                          # [MODIFIED] Document OKF + Claude Code memory feature under [Unreleased]
ACKNOWLEDGMENTS.md                    # [MODIFIED] Add Claude Code Memory and Google OKF attribution
README.md                             # [MODIFIED] Document `buddhi memory`, `buddhi_memory`, bundle layout, and skills
```

### Test Suite Layout
```text
tests/
├── test_memory_model.py              # OKF v0.2 dataclass validation, frontmatter parsing/serialization
├── test_memory_provenance.py         # SHA-256 calculation, line slicing (#L10-L25), staleness detection
├── test_memory_security.py           # Path traversal, sandbox escape, DoS caps, secret leakage scanner
├── test_memory_imports.py            # @path recursion (depth 5), circular loops, missing files
├── test_memory_budget.py             # MEMORY.md 200-line / 25KB budget validator and compaction logic
├── test_memory_migration.py          # Legacy flat-file converter, idempotency, backup verification
├── test_memory_cli.py                # CliRunner integration tests for `buddhi memory *`
└── test_memory_mcp.py                # FastMCP integration tests for `buddhi_memory` tool
```

---

## Detailed Component Specifications

### 1. OKF Frontmatter & Concept Schema (`src/buddhi/memory/models.py`)
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
  by: buddhi-cli
  at: "2026-10-26T13:20:00Z"
sources:
  - id: src-sqlite-writer
    resource: "src/buddhi/persist/sqlite_writer.py#L15-L48"
    content_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
relations:
  - kind: supersedes
    target: mem-decision-sqlite-default
---

# Summary
One-sentence summary matching frontmatter.

# Context & Rationale
Detailed explanation of why this decision was made and alternative options considered.

# Rules / Invariants
Concrete behavioral rules agents and developers must adhere to.

# References
- [SQLite WAL documentation](https://sqlite.org/wal.html)
```

### 2. Security Invariants (`src/buddhi/memory/security.py`)
- **Sandboxed Import Resolution**:
  ```python
  def resolve_and_sandbox_import(raw_ref: str, base_dir: Path, workspace_root: Path, user_memory_root: Path) -> Path
  ```
  Validates canonical paths via `resolve(strict=True)` and enforces `target.is_relative_to(workspace_root)` or `target.is_relative_to(user_memory_root)`. Rejects UNC paths (`\\\\`, `//`), null bytes, and path traversal strings (`..`).
- **Resource Anchor Validation**:
  ```python
  def parse_source_resource(resource: str, workspace_root: Path) -> tuple[Path, int | None, int | None]
  ```
  Validates relative path bounds within `workspace_root` and parses regex `^L(\d+)(?:-L(\d+))?$`.
- **Slug Sanitization**:
  ```python
  def sanitize_slug(raw_slug: str) -> str
  ```
  Permits only `[a-z0-9_-]`, strips Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, etc.), and truncates to 50 characters.
- **Secret Scanner**:
  ```python
  def assert_no_secrets_in_tracked_memory(content: str, scope: str) -> None
  ```
  Scans content against known token/key regexes (API keys, private keys, connection strings) before saving to git-tracked scopes (`project` or `agent:<name>`).

### 3. Provenance & Staleness (`src/buddhi/memory/hash.py`)
- **Anchor Slicing**:
  `compute_content_hash(root, resource)` parses `#L<start>-L<end>`, normalizes line endings (`\r\n` -> `\n`), extracts 1-indexed line ranges, and calculates `hashlib.sha256(content.encode("utf-8")).hexdigest()`.
- **Staleness Evaluation**:
  `verify_source_staleness(root, source)` returns `StalenessResult(is_stale=True, reason="hash_mismatch")` if the on-disk slice SHA-256 differs from `source.content_hash`, or `reason="file_not_found"` if the file was moved/deleted.

### 4. Resolver & Import Recursion (`src/buddhi/memory/resolver.py`)
- **Glob Matching**:
  `matches_active_files(patterns, active_files)` evaluates each pattern using `fnmatch.fnmatchcase(file_posix, pattern)` or `PurePosixPath.match()`. If `patterns` is empty, it unconditionally matches (global scope).
- **5-Hop Import Recursion**:
  `resolve_imports(text, base_file, allowed_roots, max_depth=5, visited=None)` replaces `@<path>` matches with file contents. Recursion halts and outputs error comments if depth exceeds 5 or if `target in visited` (circular import).

### 5. Multi-Scope Bundle Store (`src/buddhi/memory/store.py`)
- **Scopes**:
  - `project`: `.agents/memory/`
  - `local`: `.agents/memory.local/` (gitignored)
  - `user`: `~/.buddhi/memory/`
  - `agent:<name>`: `.agents/agent-memory/<name>/` (tracked) or `.agents/agent-memory-local/<name>/` (local)
- **Budget Enforcement**:
  `sync_indexes(scope="project")` generates `.agents/memory/MEMORY.md`:
  - Frontmatter: `okf_version: "0.2"`
  - Markdown list: `* [<title>](<relative-path>) - <summary>` (capped at `<= 150 chars` per line).
  - Hard cap: If total lines exceed 200 or byte size exceeds 25,600 bytes, `compact()` demotes `superseded`/`deprecated` or oldest `inferred` entries, keeping them accessible in `<topic>/index.md`.
- **Mutation Log**:
  `log_mutation()` prepends entries to `.agents/memory/log.md` with ISO-8601 timestamps and action types (`created`, `updated`, `superseded`, `compacted`, `migrated`, `sdd-promoted`).

### 6. Legacy Migration Engine (`src/buddhi/memory/migrate.py`)
- Detects existing `.agents/memory/user-preferences.md`, `project-conventions.md`, `tech-decisions.md`, and `feedback-history.md`.
- Strips boilerplate ("No entries yet.").
- Parses distinct entries (bullet points or numbered lists), generates unique slugs, constructs `MemoryNode` instances with OKF frontmatter, and writes them to `preferences/`, `conventions/`, `decisions/`, and `feedback/`.
- Renames legacy files to `.md.bak`.
- Rebuilds `MEMORY.md` and appends to `log.md`.
- Fully idempotent: multiple runs produce 0 duplicate nodes.

### 7. SDD Promotion Engine (`src/buddhi/memory/sdd_promote.py`)
- Reads `.buddhi/specs/<branch>/` (or `.buddhi/specs/done/<branch>/`).
- Extracts architectural decisions from `plan.md` and verified `sound` choices from `choices.md`.
- Generates `sdd-rationale` nodes under `.agents/memory/sdd/` and `decision` nodes under `.agents/memory/decisions/` with `relations: [{ kind: derived_from_spec, target: ".buddhi/specs/done/<branch>/spec.md" }]`.

### 8. CLI Interface (`src/buddhi/commands/memory.py`)
- `buddhi memory status [--scope <s...>] [--json]`
- `buddhi memory add --kind <kind> --title <title> --summary <summary> [--body <body>] [--path-glob <g...>] [--source <s...>] [--scope <scope>] [--tag <t...>]`
- `buddhi memory search <query> [--kind <kind>] [--scope <scope>] [--active-file <f...>] [--json]`
- `buddhi memory read <id_or_path> [--expand-imports]`
- `buddhi memory validate [--scope <scope>] [--json]`
- `buddhi memory sync [--scope <scope>] [--fix]`
- `buddhi memory compact [--scope <scope>]`
- `buddhi memory migrate [--force]`
- `buddhi memory sdd-promote [--branch <branch>]`

### 9. MCP Tool (`src/buddhi/mcp/tools/memory.py` & `server.py`)
- Exposes `buddhi_memory(action, query, kind, scope, active_files, node_id, title, summary, body, path_globs, sources, tags, expand_imports, branch)` on `buddhi-mcp`.
- Fully integrated with `buddhi_search` and `buddhi_read`.

---

## Complexity Tracking

| Violation / Decision | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| Custom frontmatter splitting vs external full-markdown parser | `buddhi-cli` needs instant, lightweight (<100ms) frontmatter inspection across 100+ files without AST parsing entire markdown bodies. | Heavy Markdown AST libraries (like `marko` or `mistune`) add extra dependencies and overhead for simple YAML frontmatter slicing. |
| Strict 5-hop recursion limit on `@path` | Prevents denial-of-service via deep or mutual recursive `@path` file inclusion loops. | Unbounded recursion risks stack overflows or memory exhaustion during agent context assembly. |
| Automatic demotion during `compact` | Enforces the 200-line / 25KB Claude Code context budget on `MEMORY.md` so Antigravity sessions never saturate context windows. | Discarding memories completely loses valuable history; demoting them to `<topic>/index.md` keeps them fully searchable on-demand. |

---

## Phased Execution Roadmap

### Phase 1: Core Models, Frontmatter & Security (Foundational)
- Implement `src/buddhi/memory/models.py` (OKF dataclasses and enums).
- Implement `src/buddhi/memory/frontmatter.py` (safe YAML frontmatter serializer/parser).
- Implement `src/buddhi/memory/security.py` (path traversal guard, secret scanner, slug sanitization).
- Add tests in `tests/test_memory_model.py` and `tests/test_memory_security.py`.

### Phase 2: Provenance, Resolver & Store Engine
- Implement `src/buddhi/memory/hash.py` (line-slicing `#L10-L25` & SHA-256 staleness checking).
- Implement `src/buddhi/memory/resolver.py` (glob matching & sandboxed 5-hop `@path` expansion).
- Implement `src/buddhi/memory/store.py` (multi-scope bundle management, 200-line/25KB cap, compaction, `log.md`).
- Add tests in `tests/test_memory_provenance.py`, `tests/test_memory_imports.py`, and `tests/test_memory_budget.py`.

### Phase 3: Legacy Migration, SDD Promotion & CLI
- Implement `src/buddhi/memory/migrate.py` (legacy flat-file conversion).
- Implement `src/buddhi/memory/sdd_promote.py` (spec decisions and choices extractor).
- Implement `src/buddhi/commands/memory.py` (Typer CLI commands) and mount in `src/buddhi/cli.py`.
- Update `src/buddhi/commands/init.py` and `src/buddhi/util/fsutil.py` (wire migration and `.gitignore` rules).
- Add tests in `tests/test_memory_migration.py` and `tests/test_memory_cli.py`.

### Phase 4: MCP Tool & Antigravity Harness Skills
- Implement `src/buddhi/mcp/tools/memory.py` and register `buddhi_memory` in `src/buddhi/mcp/server.py`.
- Add test in `tests/test_memory_mcp.py`.
- Update templates under `src/buddhi/templates/agents/memory/` and `.agents/memory/`.
- Update specialist agent definitions with `memory: project`.
- Add `/memory` skill; update `/remember`, `/status`, `/spec-plan`, and `/close-spec` skills.

### Phase 5: Verification & Project Documentation
- Run full test suite (`uv run pytest`), linter (`uv run ruff check .`), formatter (`uv run ruff format --check .`), and typecheck (`uv run mypy src/ tests/`).
- Update `CHANGELOG.md` under `## [Unreleased]`.
- Update `ACKNOWLEDGMENTS.md` with Claude Code Memory and Google OKF attribution.
- Update `README.md` with `buddhi memory` CLI and `buddhi_memory` MCP tool documentation.
