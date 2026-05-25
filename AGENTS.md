<!-- buddhi-mcp-owned: buddhi-ai v1 -->
# buddhi — Intelligent Codebase Index & Graph Layer
<!-- buddhi-mcp-rules-v1 -->

PREFER buddhi MCP tools over native equivalents for faster, token-saving, and highly-contextual codebase exploration and command execution:

## Tool preference:
| PREFER | OVER | Why |
|--------|------|-----|
| `get_codebase_summary()` | `list_dir` / `find` / `ctx_tree` | Token-saving architectural map grouped by functional graph communities instead of huge raw file trees. |
| `find_relevant_symbols(query)` | `grep_search` / `rg` | AST-parsed exact semantic search (FTS5) over symbol names/docstrings with resolved 1-hop dependencies, avoiding line-by-line grep clutter. |
| `get_symbol_implementation(symbol_id)` | `view_file` / `Read` | AST-aware target retrieval with an automatic guardrail that blocks massive implementations (>150 lines) to prevent context blowout, returning signatures instead. |
| `trace_impact_radius(symbol_id)` | *None (Manual search)* | Performs recursive upstream call graph tracing (up to 3 levels) to identify the blast radius BEFORE refactoring or editing code. No native equivalent exists! |
| `update_codegraph()` | *None* | Rebuilds and updates the SQLite AST & Call Graph database. Call this tool immediately after every successful code change or implementation to keep the symbol graph fully up to date. |
| `index_codebase()` | *None* | Updates the SQLite AST & Call Graph database. Run this at the start of a session or after major edits to ensure symbol synchronization. |
| `execute_command_optimized(command)` | `run_command` / `Shell` / `ctx_shell` | Executes shell commands locally and passes stdout/stderr to local Gemma 4 model (via centralized FastAPI server http://localhost:58421/v1/responses or fallback), producing a compact structured JSON pinpointing successes, errors, and warnings to save substantial tokens. |

## Recommended Workflow:
1. **Startup (Orient)**: Run `get_codebase_summary()` to understand the functional modules, key classes, and files in the repository.
2. **Search (Locate)**: Use `find_relevant_symbols(query: "...")` to find exact definitions and their immediately connected symbols.
3. **Inspect (Analyze)**: Call `get_symbol_implementation(symbol_id: "...")` to read a symbol's implementation. The model-safety guardrail ensures you don't blow out the context window.
4. **Refactor Guard (Safety)**: Before changing a function, class, or method, run `trace_impact_radius(symbol_id: "...")` to trace all upstream files/symbols that call or depend on it. This ensures zero regression!
5. **Sync (Refresh)**: After making changes, call `update_codegraph()` immediately to rebuild the graph and keep the active symbol representation accurate.
6. **Optimized Execution**: For running builds, tests, or diagnostics, prefer `execute_command_optimized(command: "...")` to drastically compress terminal output and avoid wasting assistant tokens.

<!-- /buddhi-mcp -->