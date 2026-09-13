# Feature Specification: Codebase Q&A Workflow (/ask), Graph Refresh Integration, and MCP Root Configuration

**Feature Branch**: `002-ask-workflow-and`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description:
1. Add new workflow `/ask` for Agent Initialization (`buddhi init`) to answer user queries using the code graph, running `buddhi generate` before executing.
2. In `/specify`, `/debug`, and `/quick-plan` workflows, always start by running `buddhi generate` to update the code graph.
3. In `buddhi init`, configure the repo root path in `.agents/mcp_config.json` `args` so Antigravity only needs to pass `query` when using `buddhi_search` / `buddhi_read`.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Workspace Root in MCP Config & Support `--root` in MCP Server (Priority: P1)

When an agent or user runs `buddhi init`, the scaffolded `.agents/mcp_config.json` should automatically configure the target repository's resolved root directory as an argument to `buddhi-mcp`. The `buddhi-mcp` server (and `buddhi mcp` CLI command) must accept `--root` to anchor database resolution and fallback workspace file reads/searches, allowing Antigravity agent tools (`buddhi_search` and `buddhi_read`) to succeed when called with only the `query` parameter.

**Why this priority**:
Currently, when Antigravity spawns the MCP server from a different working directory or invokes `buddhi_search` without passing an explicit `cwd`, the tool fails because it cannot find `.buddhi/graphs/tree-graph.db`. Fixing this is essential for all graph-dependent agent workflows to function reliably.

**Independent Test**:
1. Run `buddhi init <target_dir>`.
2. Inspect `<target_dir>/.agents/mcp_config.json` and verify `args` contains `["--root", "<resolved-target-dir>"]`.
3. Launch `buddhi-mcp --root <target_dir>` (or execute tool directly with `OVERRIDE_ROOT` set) from outside `<target_dir>`, call `buddhi_search(query="...")` with `cwd=None`, and verify it locates the database and returns search results.

**Acceptance Scenarios**:
1. **Given** a directory initialized with `buddhi init`, **When** `.agents/mcp_config.json` is generated or synced, **Then** `mcpServers.buddhi.args` contains `["--root", "<resolved_root_path>"]`.
2. **Given** `buddhi-mcp` is launched with `--root <path>`, **When** a tool call to `buddhi_search` or `buddhi_read` is received without `cwd`, **Then** the database path is resolved from `<path>/.buddhi/graphs/tree-graph.db` rather than the process's working directory.
3. **Given** `buddhi-mcp` is launched with `--root <path>` and a fallback file read or search occurs, **Then** relative paths and native searches are anchored to `<path>`.
4. **Given** `buddhi mcp` CLI command is run with `--root <path>`, **Then** it accepts the argument and forwards it to the MCP server.

---

### User Story 2 - Add `/ask` Workflow for Codebase Q&A Using the Code Graph (Priority: P2)

When working in an initialized repository, a developer can run `/ask <question>` to ask questions about how the codebase works, where symbols or logic are defined, and how components interact. The workflow will first run `buddhi generate` via `terminal-runner` to update the code graph, then query the graph using `buddhi_search` and `buddhi_read` (or SQLite `tree-graph.db`), and present a concise, grounded explanation citing exact file paths and line numbers without altering code or generating plan documents.

**Why this priority**:
Empowers developers and coding agents to explore and understand unfamiliar or complex codebases quickly and accurately using the topological code graph and OKF documentation.

**Independent Test**:
1. Scaffold an agent harness using `buddhi init`.
2. Verify `.agents/workflows/ask.md` and template `src/buddhi/templates/agents/workflows/ask.md` exist and define the `/ask` command with `terminal-runner` and `okf-context`.
3. Verify the workflow instructions prescribe:
   - Step 1: Execute `buddhi generate` via `terminal-runner`.
   - Step 2: Query the code graph via `buddhi_search` and `buddhi_read`.
   - Step 3: Present grounded answers citing exact `file:line` references.

**Acceptance Scenarios**:
1. **Given** an initialized workspace, **When** `/ask` is triggered with a user query, **Then** the agent first executes `buddhi generate` to ensure graph freshness before attempting to answer.
2. **Given** the code graph is generated/refreshed, **When** `/ask` executes, **Then** it queries the graph (`buddhi_search` / `buddhi_read`) for relevant symbols, call sites, and communities.
3. **Given** results from the code graph, **When** `/ask` responds to the user, **Then** the response provides specific `file:line` citations and explanations without writing code changes or creating SDD specs.

---

### User Story 3 - Pre-Execution `buddhi generate` in `/specify`, `/debug`, and `/quick-plan` (Priority: P3)

Before performing any requirements grounding in `/specify`, bug investigation in `/debug`, or lightweight planning in `/quick-plan`, each workflow must always start by executing `buddhi generate` (via the `terminal-runner` agent) to update the code graph with the latest changes in the repository.

**Why this priority**:
Prevents stale graph queries and missing symbols when code has changed between agent sessions or git branches, guaranteeing that downstream tools and specialist agents operate on current codebase facts.

**Independent Test**:
1. Inspect `src/buddhi/templates/agents/workflows/specify.md` (and `.agents/workflows/specify.md`): verify Step 1 runs `buddhi generate` via `terminal-runner`.
2. Inspect `src/buddhi/templates/agents/workflows/debug.md` (and `.agents/workflows/debug.md`): verify Step 1 runs `buddhi generate` via `terminal-runner`.
3. Inspect `src/buddhi/templates/agents/workflows/quick-plan.md` (and `.agents/workflows/quick-plan.md`): verify Step 1 runs `buddhi generate` via `terminal-runner`.

**Acceptance Scenarios**:
1. **Given** a user invokes `/specify`, **When** the workflow begins, **Then** Step 1 runs `buddhi generate` before scaffolding or grounding against the codebase.
2. **Given** a user invokes `/debug`, **When** the workflow begins, **Then** Step 1 runs `buddhi generate` before candidate root causes and graph queries are evaluated.
3. **Given** a user invokes `/quick-plan`, **When** the workflow begins, **Then** Step 1 runs `buddhi generate` so the code graph reflects the current source tree before domain classification.

---

### Edge Cases

- **Missing tree-sitter parsers / unsupported files during `buddhi generate`**: `buddhi generate` outputs warnings but exits cleanly (code 0), allowing workflows to proceed gracefully.
- **Repository moved or initialized with relative path**: `buddhi init` resolves the path with `.resolve()` to store an absolute path in `mcp_config.json`.
- **Existing `.agents/mcp_config.json` with empty `args`**: `buddhi init` idempotently ensures the `buddhi` server configuration in `mcp_config.json` has `args: ["--root", ...]` if not already configured.
- **MCP server started without `--root` argument**: Falls back gracefully to traversing upwards from CWD (existing behavior) so backwards compatibility is retained.
- **Spaces in directory paths**: Ensure path strings with spaces in `args` and CLI arguments are handled safely without shell-splitting errors.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `buddhi-mcp` CLI entrypoint in `src/buddhi/mcp/server.py` MUST accept `--root` (and positional root argument) to set the workspace root directory.
- **FR-002**: `src/buddhi/mcp/server.py` MUST store the configured root directory in `OVERRIDE_ROOT` and use it in `_get_db_path()` to locate `.buddhi/graphs/tree-graph.db` when `cwd` is omitted or null.
- **FR-003**: `execute_buddhi_read` and `execute_buddhi_search` MUST use the configured `OVERRIDE_ROOT` for relative file paths and native fallback searches.
- **FR-004**: `buddhi mcp` command in `src/buddhi/commands/mcp.py` MUST accept `--root` option and configure `OVERRIDE_ROOT`.
- **FR-005**: `buddhi init` command in `src/buddhi/commands/init.py` MUST configure `.agents/mcp_config.json` so that `mcpServers.buddhi.args` contains `["--root", "<resolved_root_path>"]`.
- **FR-006**: A new workflow file `src/buddhi/templates/agents/workflows/ask.md` MUST be created defining `/ask`, requiring `terminal-runner` agent and `okf-context` skill.
- **FR-007**: The `/ask` workflow MUST specify running `buddhi generate` via `terminal-runner` as its first step before querying the code graph.
- **FR-008**: The `/ask` workflow MUST guide the agent to answer questions grounded in `buddhi_search` and `buddhi_read` with `file:line` citations.
- **FR-009**: `src/buddhi/templates/agents/workflows/specify.md` MUST be updated so that the workflow begins by running `buddhi generate` via `terminal-runner`.
- **FR-010**: `src/buddhi/templates/agents/workflows/debug.md` MUST be updated so that the workflow begins by running `buddhi generate` via `terminal-runner`.
- **FR-011**: `src/buddhi/templates/agents/workflows/quick-plan.md` MUST be updated so that Step 1 runs `buddhi generate` via `terminal-runner`.
- **FR-012**: `buddhi init` harness synchronization MUST include `workflows/ask.md` when populating `.agents/`.
- **FR-013**: Existing active `.agents/` workflows and `mcp_config.json` in the current repository MUST be updated to reflect these enhancements.

---

### Key Entities

- **MCP Configuration (`mcp_config.json`)**: Antigravity configuration file declaring registered MCP servers, executable commands, arguments (`args`), and environment variables.
- **Ask Workflow (`workflows/ask.md`)**: Workflow definition for codebase comprehension and interactive Q&A.
- **Graph Pipeline Runner (`buddhi generate`)**: CLI command that scans source files, parses ASTs via tree-sitter, computes Louvain community clusters, and persists JSON, SQLite (`tree-graph.db`), and HTML graph artifacts.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `buddhi init` produces an `.agents/mcp_config.json` containing `args: ["--root", "<resolved_path>"]` matching the initialized root.
- **SC-002**: An agent calling `buddhi_search(query="<term>")` without providing `cwd` successfully retrieves results when the MCP server is initialized with `--root`.
- **SC-003**: 100% of the specified workflows (`/ask`, `/specify`, `/debug`, `/quick-plan`) explicitly document executing `buddhi generate` as Step 1.
- **SC-004**: `pytest` test suite passes completely, including unit and CLI tests for `init`, `mcp`, and workflow template presence.

---

## Assumptions

- Users have Python >= 3.10 and `buddhi-ai` installed in their environment.
- The `terminal-runner` agent is available in the Antigravity harness to run non-interactive CLI commands like `buddhi generate`.
- Existing customized harness files under `.agents/` in client repositories follow `buddhi init`'s idempotent update pattern.
