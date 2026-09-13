# Implementation Plan: Codebase Q&A Workflow (/ask), Graph Refresh Integration, and MCP Root Configuration

**Branch**: `002-ask-workflow-and` | **Date**: 2026-09-13 | **Spec**: [.buddhi/specs/002-ask-workflow-and/spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/002-ask-workflow-and/spec.md)

**Input**: Feature specification from `/.buddhi/specs/002-ask-workflow-and/spec.md`

## Summary

This feature enhances developer and agent workflow experiences with three interconnected improvements:
1. **MCP Server Root Configuration**: Introduces `--root` CLI argument and `OVERRIDE_ROOT` global variable in `buddhi-mcp` (and `buddhi mcp`). Updates `buddhi init` to automatically configure `args: ["--root", "<resolved_path>"]` in `.agents/mcp_config.json`, eliminating search/read failures in Antigravity caused by missing `cwd`.
2. **`/ask` Codebase Q&A Workflow**: Adds a dedicated conversational Q&A workflow template and agent workflow that runs `buddhi generate` to update the code graph before answering questions using `buddhi_search` and `buddhi_read` with `file:line` citations.
3. **Pre-Execution `buddhi generate` in Existing Workflows**: Updates `/specify`, `/debug`, and `/quick-plan` workflows to always execute `buddhi generate` as Step 1 to guarantee fresh code graph state before grounding or reasoning.

---

## Technical Context

**Language/Version**: Python >= 3.10  
**Primary Dependencies**: FastMCP (`mcp[cli]>=1.2.0,<2.0.0`), Typer, Rich, SQLite3, Tree-sitter  
**Storage**: SQLite (`.buddhi/graphs/tree-graph.db`), JSON (`tree-graph.json`, `.agents/mcp_config.json`), Markdown (workflow definitions)  
**Testing**: `pytest` (`pytest>=9.1.1`), `CliRunner`  
**Target Platform**: Cross-platform (Windows, Linux, macOS)  
**Project Type**: CLI tool and MCP Server  
**Performance Goals**: Instant resolution of `--root` without overhead; `buddhi init` finishes within 2 seconds for typical repos; tool calls resolve paths directly via `OVERRIDE_ROOT`.  
**Constraints**: Fully backwards-compatible with existing `buddhi-mcp` invocations without `--root`; idempotent `buddhi init`.  
**Scale/Scope**: 5 modified files in `src/`, 1 new workflow template in `src/`, 4 updated workflows in `.agents/`, and updated test cases.

---

## AGENTS.md Compliance Check

- [x] Project build & test commands adhered to (`uv run pytest`, `uv run ruff check .`)
- [x] Architectural constraints respected (Clean separation between CLI commands, MCP server, templates, and harness sync)
- [x] No unapproved external dependencies introduced (Uses standard library `argparse`, `pathlib`, `json` and existing FastMCP / Typer)

---

## Project Structure

### Documentation (this feature)

```text
.buddhi/specs/002-ask-workflow-and/
├── spec.md              # Feature specification
└── plan.md              # This file (/plan command output)
```

### Source Code & Template Changes

```text
src/buddhi/
├── mcp/
│   ├── server.py                        # Add --root argument, OVERRIDE_ROOT, update _get_db_path()
│   └── tools/
│       ├── search.py                    # Support OVERRIDE_ROOT in _native_grep_search & execute_buddhi_search
│       └── read.py                      # Support OVERRIDE_ROOT in relative filepath resolution and fallback glob
├── commands/
│   ├── mcp.py                           # Add --root option to buddhi mcp CLI command
│   └── init.py                          # Automatically inject ["--root", str(root)] into .agents/mcp_config.json
└── templates/agents/
    ├── templates/
    │   └── agents-template.md           # Add /ask to AGENTS.md template command list
    └── workflows/
        ├── ask.md                       # [NEW] Codebase Q&A workflow template
        ├── specify.md                   # Update Step 1 to run buddhi generate
        ├── debug.md                     # Update Step 1 to run buddhi generate
        └── quick-plan.md                # Update Step 1 to run buddhi generate

.agents/
├── mcp_config.json                      # Update args with --root for active workspace
└── workflows/
    ├── ask.md                           # [NEW] Active workspace ask workflow
    ├── specify.md                       # Active workspace update
    ├── debug.md                         # Active workspace update
    └── quick-plan.md                    # Active workspace update

tests/
├── test_cli_init.py                     # Verify workflows/ask.md and mcp_config.json args
├── test_mcp_server.py                   # Verify --root argument and OVERRIDE_ROOT path resolution
└── test_sdd.py                          # Fix test_sdd_dry_run_create working directory isolation
```

---

## Detailed Implementation Steps

### Phase 1: MCP Server & CLI `--root` Support (User Story 1 - P1)

1. **Modify `src/buddhi/mcp/server.py`**:
   - Add global `OVERRIDE_ROOT: Path | None = None`.
   - Update `_get_db_path(cwd: str | None = None) -> Path`:
     ```python
     if OVERRIDE_DB_PATH is not None:
         return OVERRIDE_DB_PATH
     start_dir = Path(cwd).resolve() if cwd else (OVERRIDE_ROOT if OVERRIDE_ROOT is not None else Path.cwd().resolve())
     ```
   - Update `main()` to accept `--root` and positional `root_dir`:
     ```python
     parser.add_argument("--root", type=str, help="Workspace root directory")
     parser.add_argument("root_dir", nargs="?", type=str, default=None, help="Workspace root directory")
     ```
     When parsed, set `OVERRIDE_ROOT = Path(root_val).resolve()`.
   - Update `buddhi_search` and `buddhi_read` to forward `OVERRIDE_ROOT` if `cwd` is omitted.

2. **Modify `src/buddhi/mcp/tools/search.py` and `src/buddhi/mcp/tools/read.py`**:
   - In `search.py`, allow `_native_grep_search` to accept a base directory, defaulting to `OVERRIDE_ROOT` if set.
   - In `read.py`, allow relative filepaths to be checked against `OVERRIDE_ROOT` if not found in current directory.

3. **Modify `src/buddhi/commands/mcp.py`**:
   - Add `--root` / `-r` option to `buddhi mcp` CLI command and forward it to `server_mod.OVERRIDE_ROOT`.

4. **Modify `src/buddhi/commands/init.py`**:
   - After `sync_template_tree(template_dir, root / ".agents")`:
     Locate `mcp_config_path = root / ".agents" / "mcp_config.json"`.
     If it exists, parse JSON, ensure `mcpServers.buddhi.args = ["--root", str(root.resolve())]`, and save back cleanly.

---

### Phase 2: Create `/ask` Workflow Template and Agent Harness File (User Story 2 - P2)

1. **Create `src/buddhi/templates/agents/workflows/ask.md`**:
   - YAML frontmatter: `name: ask`, `description: Answer user questions about the codebase using the code graph...`, `requires_agents: terminal-runner`, `requires_skills: okf-context`.
   - Step 1: **Update code graph**: Run `buddhi generate` via `terminal-runner`.
   - Step 2: **Query code graph and docs**: Use `buddhi_search` and `buddhi_read` to find relevant nodes, call sites, and communities.
   - Step 3: **Synthesize answer**: Ground answers with exact `file:line` citations without making edits.

2. **Scaffold to `.agents/workflows/ask.md`**:
   - Place active copy in `.agents/workflows/ask.md`.
   - Update `AGENTS.md` and `src/buddhi/templates/agents/templates/agents-template.md` to reference `/ask`.

---

### Phase 3: Pre-Execution `buddhi generate` in Existing Workflows (User Story 3 - P3)

1. **Update `src/buddhi/templates/agents/workflows/specify.md` & `.agents/workflows/specify.md`**:
   - Add Step 1: **Update code graph**: Run `buddhi generate` via `terminal-runner`.
   - Renumber subsequent steps cleanly.

2. **Update `src/buddhi/templates/agents/workflows/debug.md` & `.agents/workflows/debug.md`**:
   - Add Step 1: **Update code graph**: Run `buddhi generate` via `terminal-runner`.
   - Renumber subsequent steps cleanly.

3. **Update `src/buddhi/templates/agents/workflows/quick-plan.md` & `.agents/workflows/quick-plan.md`**:
   - Update Step 1: Run `buddhi generate` via `terminal-runner` so `.buddhi/graphs/` and `.buddhi/docs-plan.json` reflect the latest source tree.

---

### Phase 4: Test Suite Updates and Verification

1. **Update `tests/test_cli_init.py`**:
   - Verify `(agents_dir / "workflows" / "ask.md").exists()`.
   - Verify `mcp_cfg["mcpServers"]["buddhi"]["args"] == ["--root", str(tmp_path.resolve())]`.

2. **Update `tests/test_mcp_server.py`**:
   - Add test case verifying `--root` argument sets `OVERRIDE_ROOT` and `_get_db_path()` discovers `<root>/.buddhi/graphs/tree-graph.db`.
   - Add test case verifying `buddhi_search` succeeds with `OVERRIDE_ROOT` when process CWD is different.

3. **Update `tests/test_sdd.py`**:
   - Isolate `test_sdd_dry_run_create` using `tmp_path` and `monkeypatch.chdir(tmp_path)`.

4. **Run Full Verification**:
   - Run `uv run pytest` to achieve 100% test pass rate.
   - Run `uv run ruff check .` to verify formatting and lint standards.

---

## Complexity Tracking

*No architectural violations or unnecessary abstractions introduced. Reuses existing CLI patterns, FastMCP lifecycle, and template synchronization.*
