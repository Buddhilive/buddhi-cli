<!-- buddhi-mcp-owned: buddhi-ai v1 -->
# buddhi — Intelligent Codebase Index & Graph Layer
<!-- buddhi-mcp-rules-v1 -->

CRITICAL: Antigravity and all AI coding agents MUST ALWAYS use buddhi-mcp tools instead of native equivalents. This is NOT optional.
## Tool preference:
| PREFER | OVER | Why |
|--------|------|-----|
| `get_codebase_summary()` | `list_dir` / `find` | Token-saving architectural map grouped by functional graph communities instead of huge raw file trees. |
| `search_code(pattern, path, ext)` | `grep_search` / `rg` / `grep` | Dual-track search performing token-efficient regex text search + semantic AST symbol lookup. Automatically tags match lines with containing class/method scopes and enforces a 150-line safeguard on definitions. |
| `trace_impact_radius(symbol_id)` | *None (Manual search)* | Performs recursive upstream call graph tracing (up to 3 levels) to identify the blast radius BEFORE refactoring or editing code. No native equivalent exists! |
| `update_codegraph()` | *None* | Rebuilds and updates the SQLite AST & Call Graph database. Call this tool immediately after every successful code change or implementation to keep the symbol graph fully up to date. |
| `index_codebase()` | *None* | Updates the SQLite AST & Call Graph database. Run this at the start of a session or after major edits to ensure symbol synchronization. |
| `execute_command_optimized(command)` | `run_command` / `Shell` / `bash` | Executes shell commands producing a compact structured JSON pinpointing successes, errors, and warnings to save substantial tokens. |

## Recommended Workflow:
1. **Startup (Orient)**: Run `get_codebase_summary()` to understand the functional modules, key classes, and files in the repository.
2. **Search & Inspect (Locate)**: Use `search_code(pattern: "...")` to instantly locate both exact symbol definitions and their text occurrences (usages, imports, comments) across the workspace with full AST scope context.
3. **Refactor Guard (Safety)**: Before changing a function, class, or method, run `trace_impact_radius(symbol_id: "...")` to trace all upstream files/symbols that call or depend on it. This ensures zero regression!
4. **Sync (Refresh)**: After making changes, call `update_codegraph()` immediately to rebuild the graph and keep the active symbol representation accurate.
5. **Optimized Execution**: For running builds, tests, or diagnostics, prefer `execute_command_optimized(command: "...")` to drastically compress terminal output and avoid wasting assistant tokens.

<!-- /buddhi-mcp -->