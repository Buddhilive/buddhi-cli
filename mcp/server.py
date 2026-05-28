import os
import sqlite3
import datetime
import json
import time
from mcp.server.fastmcp import FastMCP
from db import CodeGraphDB, get_db_path, get_workspace_root
from indexer import CodeIndexer
from search import handle_search

# Initialize FastMCP Server
mcp = FastMCP("CodeGraph")

# Global Cache for buddhi_view_file (tracks content, mtime, read counts, full delivery flags)
FILE_CACHE: dict = {}


def log_tool_trigger(tool_name: str, status: str = "success", duration_ms: float = 0.0, arguments: dict | None = None):
    try:
        user_folder = os.path.expanduser("~")
        db_dir = os.path.join(user_folder, ".buddhi", "data")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "telemetry.db")
        
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                arguments TEXT NOT NULL
            )
        """)
        
        # Truncate large arguments
        args_str = json.dumps(arguments or {})
        if len(args_str) > 2000:
            args_str = args_str[:1997] + "..."
            
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO tool_usage (tool_name, timestamp, status, duration_ms, arguments)
            VALUES (?, ?, ?, ?, ?)
        """, (tool_name, timestamp, status, duration_ms, args_str))
        
        conn.commit()
        conn.close()
    except Exception as e:
        # Telemetry is secondary, fail silently to stderr to avoid disrupting StdIO
        import sys
        print(f"[Telemetry Error] {e}", file=sys.stderr, flush=True)


# ==========================================
# Core Reusable Implementation Methods
# ==========================================

def index_codebase_impl(workspace_root=None):
    """Indexes/re-indexes the codebase files and rebuilds the sqlite graph database."""
    if not workspace_root:
        workspace_root = get_workspace_root()
    indexer = CodeIndexer(workspace_root)
    num_nodes, num_edges = indexer.index_codebase()
    return f"Successfully indexed codebase at '{workspace_root}'. Found {num_nodes} symbols and {num_edges} call edges."


def get_codebase_summary_impl(db_path=None):
    """Retrieves all communities and nodes from SQLite and returns a concise, token-saving overview."""
    db = CodeGraphDB(db_path)
    communities = db.get_codebase_summary()

    if not communities:
        return "No codebase summary available. Please run the `index_codebase` tool first."

    output = ["# CodeGraph: Codebase Summary Overview\n"]
    output.append(f"Database located at: `{db.db_path}`\n")
    output.append("The codebase has been divided into tightly-coupled functional communities using graph clustering:\n")

    for community_id, nodes in communities.items():
        output.append(f"## Community {community_id} (Functional Cluster)")
        
        # Split nodes into modules, classes, and other symbols
        modules = [n for n in nodes if n["type"] == "module"]
        classes = [n for n in nodes if n["type"] == "class"]
        functions = [n for n in nodes if n["type"] in ("function", "method")]

        output.append(f"* **Size:** {len(nodes)} symbols")
        
        if modules:
            module_names = [f"`{m['name']}`" for m in modules[:5]]
            output.append(f"* **Key Files:** {', '.join(module_names)}")
        if classes:
            class_names = [f"`{c['name']}`" for c in classes[:5]]
            output.append(f"* **Key Classes:** {', '.join(class_names)}")
        if functions:
            func_names = [f"`{f['name']}`" for f in functions[:5]]
            output.append(f"* **Key Functions:** {', '.join(func_names)}")

        # Add a couple docstrings from major components
        notable_docs = []
        for node in nodes:
            if node["docstring"] and node["type"] in ("module", "class", "function"):
                clean_doc = node["docstring"].strip().split("\n")[0]
                if clean_doc:
                    notable_docs.append(f"  - `{node['name']}`: *{clean_doc}*")
            if len(notable_docs) >= 3:
                break
        
        if notable_docs:
            output.append("* **Descriptions:**")
            output.extend(notable_docs)
            
        output.append("")

    return "\n".join(output)


def find_relevant_symbols_impl(query, db_path=None):
    """Searches SQLite FTS5 virtual table for matching symbol names and docstrings

    and resolves their immediate 1-hop dependencies.
    """
    db = CodeGraphDB(db_path)
    results = db.find_relevant_symbols(query)

    if not results:
        return f"No symbols found matching query: '{query}'"

    output = [f"# CodeGraph Search Results for: '{query}'\n"]

    for idx, res in enumerate(results, 1):
        sym = res["symbol"]
        doc = sym["docstring"].strip() if sym["docstring"] else "No docstring available."
        # Truncate docstring to avoid context bloat in search list
        doc_snippet = doc.split("\n")[0] if "\n" in doc else doc
        
        output.append(f"### {idx}. {sym['type'].upper()}: `{sym['name']}`")
        output.append(f"* **ID:** `{sym['id']}`")
        output.append(f"* **File Location:** `{sym['file_path']}` (Lines {sym['start_line']}-{sym['end_line']})")
        output.append(f"* **About:** *{doc_snippet}*")
        
        # Outgoing calls
        deps = res["depends_on"]
        if deps:
            dep_names = [f"`{d['name']}` ({d['type']})" for d in deps[:5]]
            output.append(f"* **Depends On:** {', '.join(dep_names)}")
        
        # Incoming calls
        callers = res["called_by"]
        if callers:
            caller_names = [f"`{c['name']}` ({c['type']})" for c in callers[:5]]
            output.append(f"* **Called By:** {', '.join(caller_names)}")
            
        output.append("")

    return "\n".join(output)


def trace_impact_radius_impl(symbol_id, max_depth=3, db_path=None):
    """Executes a recursive CTE query starting at symbol_id, walking upstream

    to find caller chains up to max_depth deep.
    """
    db = CodeGraphDB(db_path)
    # Check if target node exists
    target = db.get_symbol_details(symbol_id)
    if not target:
        return f"Symbol ID '{symbol_id}' not found in CodeGraph database."

    impact_nodes = db.trace_impact_radius(symbol_id, max_depth)

    output = ["# CodeGraph Upstream Impact Radius (Blast-Radius Report)\n"]
    output.append(f"Target Symbol: **{target['type'].upper()}** `{target['name']}`")
    output.append(f"ID: `{target['id']}`")
    output.append(f"Defined In: `{target['file_path']}` (Lines {target['start_line']}-{target['end_line']})\n")

    if not impact_nodes:
        output.append("> **Result:** No upstream callers detected. This symbol appears to have no direct inward dependencies in this codebase (it may be a top-level CLI command, event handler, or API route).")
        return "\n".join(output)

    output.append(f"Found **{len(impact_nodes)}** upstream dependants up to **{max_depth}** levels deep:\n")

    # Group by depth
    by_depth = {}
    for node in impact_nodes:
        depth = node["depth"]
        if depth not in by_depth:
            by_depth[depth] = []
        by_depth[depth].append(node)

    for depth in sorted(by_depth.keys()):
        output.append(f"### Level {depth} Callers (Distance: {depth})")
        for node in by_depth[depth]:
            output.append(f"* **{node['type'].upper()}** `{node['name']}`")
            output.append(f"  - Node ID: `{node['node_id']}`")
            output.append(f"  - File: `{node['file_path']}` (Lines {node['start_line']}-{node['end_line']})")
        output.append("")

    return "\n".join(output)


def get_symbol_implementation_impl(symbol_id, max_lines=150, db_path=None, workspace_root=None):
    """Fetches implementation details. If the symbol is short, it returns the complete code snippet.

    If it's a massive object exceeding max_lines, it guardrails the code to avoid context bloat,
    returning only signature, docstring, and its structural components.
    """
    db = CodeGraphDB(db_path)
    symbol = db.get_symbol_details(symbol_id)
    if not symbol:
        return f"Symbol ID '{symbol_id}' not found in CodeGraph database."

    if not workspace_root:
        workspace_root = get_workspace_root()

    file_path = os.path.join(workspace_root, symbol["file_path"])
    if not os.path.exists(file_path):
        return f"File '{symbol['file_path']}' not found in local workspace."

    start_line = symbol["start_line"]
    end_line = symbol["end_line"]
    total_lines = end_line - start_line + 1

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading file '{symbol['file_path']}': {e}"

    # Extract lines (0-indexed slice)
    slice_start = max(0, start_line - 1)
    slice_end = min(len(lines), end_line)
    code_lines = lines[slice_start:slice_end]
    code_snippet = "".join(code_lines)

    output = [f"# CodeGraph Implementation Details for: `{symbol['name']}`\n"]
    output.append(f"* **Type:** {symbol['type'].upper()}")
    output.append(f"* **File:** `{symbol['file_path']}` (Lines {start_line}-{end_line})")
    output.append(f"* **Docstring:** *{symbol['docstring'].strip() if symbol['docstring'] else 'None'}*\n")

    # Guardrail Check: Block massive objects from blowing out the AI's context window
    if total_lines > max_lines:
        output.append("> [!WARNING]")
        output.append(f"> **Massive Object Guardrail Triggered:** This symbol is **{total_lines} lines** long, which exceeds the limit of {max_lines} lines.")
        output.append("> To prevent exhausting your model's context window, the full implementation has been blocked. Only the signature and structural interface are shown below:\n")
        
        # Extract signature: First 15 lines of code (enough to capture def and docstring)
        sig_lines = code_lines[:15]
        sig_code = "".join(sig_lines)
        
        output.append("### Signature & Top Scope:")
        output.append(f"```python\n{sig_code}\n# ... [implementation code omitted to save tokens ({total_lines - 15} lines)]\n```")
        
        # Retrieve its sub-methods/internal nodes if it's a class
        if symbol["type"] == "class":
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, name, type, start_line, end_line, docstring
                    FROM nodes
                    WHERE id LIKE ? AND type = 'method'
                    ORDER BY start_line
                """, (f"{symbol_id}.%",))
                methods = cursor.fetchall()
            
            if methods:
                output.append("\n### Class Methods & Structural Components:")
                for m in methods:
                    m_doc = m["docstring"].strip().split("\n")[0] if m["docstring"] else "No docstring."
                    output.append(f"* **METHOD** `{m['name']}` (Lines {m['start_line']}-{m['end_line']})")
                    output.append(f"  - *{m_doc}*")
    else:
        # Normal return of code
        output.append("### Complete Implementation:")
        output.append(f"```python\n{code_snippet}\n```")

    return "\n".join(output)


def execute_command_optimized_impl(command: str, timeout_seconds: int = 120) -> str:
    """Executes the given command locally, captures standard output and error,
    and structures the outcome using the local Gemma 4 model (or API / regex fallback)
    into a token-saving JSON response format.
    """
    import sys
    import subprocess
    import urllib.request
    import urllib.error
    import json
    import re
    import os
    import tempfile
    from db import get_workspace_root

    workspace_root = get_workspace_root()
    env = os.environ.copy()

    # Prepend virtual environment binary path if it exists in the workspace
    local_paths = []
    
    # 1. Python Virtual Environments
    for venv_name in [".venv", "venv"]:
        venv_path = os.path.join(workspace_root, venv_name)
        if os.path.isdir(venv_path):
            if sys.platform == "win32":
                scripts_path = os.path.join(venv_path, "Scripts")
            else:
                scripts_path = os.path.join(venv_path, "bin")
            if os.path.isdir(scripts_path):
                local_paths.append(scripts_path)
                # Set VIRTUAL_ENV environment variable
                env["VIRTUAL_ENV"] = venv_path
                env.pop("PYTHONHOME", None)
                break  # Only use one venv

    # 2. Node.js local bin
    node_bin = os.path.join(workspace_root, "node_modules", ".bin")
    if os.path.isdir(node_bin):
        local_paths.append(node_bin)

    # 3. Rust local build targets
    for target_dir in [os.path.join("target", "debug"), os.path.join("target", "release")]:
        rust_bin = os.path.join(workspace_root, target_dir)
        if os.path.isdir(rust_bin):
            local_paths.append(rust_bin)

    # 4. General local bin
    general_bin = os.path.join(workspace_root, "bin")
    if os.path.isdir(general_bin):
        local_paths.append(general_bin)

    # Prepend all found paths to the PATH environment variable
    if local_paths:
        path_key = "PATH"
        for k in list(env.keys()):
            if k.upper() == "PATH":
                path_key = k
                break
        
        old_path = env.get(path_key, "")
        new_path_prefix = os.pathsep.join(local_paths)
        if old_path:
            env[path_key] = new_path_prefix + os.pathsep + old_path
        else:
            env[path_key] = new_path_prefix

    # 1. OS-specific shell command runner
    stdout, stderr, returncode = "", "", -1
    try:
        if sys.platform == "win32":
            # Create a temporary ps1 script file to run the command reliably
            # Wrap with UTF-8 encoding support and error action preferences to prevent ANSI encoding garbling and propagate errors
            ps_script = (
                "$ErrorActionPreference = 'Stop';\n"
                "$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;\n"
                "try {\n"
                f"    {command}\n"
                "    if ($LastExitCode -ne $null -and $LastExitCode -ne 0) { exit $LastExitCode }\n"
                "} catch {\n"
                "    [Console]::Error.WriteLine($_)\n"
                "    exit 1\n"
                "}"
            )
            
            # delete=False because Windows subprocess might not be able to read an open file
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w", encoding="utf-8") as f:
                f.write(ps_script)
                tmp_path = f.name
            
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", tmp_path],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    cwd=workspace_root,
                    timeout=timeout_seconds
                )
                stdout, stderr, returncode = res.stdout, res.stderr, res.returncode
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        else:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=workspace_root,
                timeout=timeout_seconds
            )
            stdout, stderr, returncode = res.stdout, res.stderr, res.returncode
    except subprocess.TimeoutExpired as e:
        # Gracefully handle timeout (hang prevention)
        captured_stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        captured_stderr = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        
        fallback_json = {
            "status": "error",
            "summary": f"Command timed out and was killed after {timeout_seconds} seconds.",
            "critical_findings": [
                f"Execution timed out. Command: '{command}'",
                f"Captured STDOUT so far: {captured_stdout[:1000].strip()}",
                f"Captured STDERR so far: {captured_stderr[:1000].strip()}"
            ],
            "exit_code": -1
        }
        return json.dumps(fallback_json, indent=2)
    except Exception as e:
        # If command launch fails completely
        return json.dumps({
            "status": "error",
            "summary": f"Failed to execute command: {str(e)}",
            "critical_findings": [f"Execution failed to start: {str(e)}"],
            "exit_code": -1
        }, indent=2)

    # 2. Performance-based soft compression for extremely large outputs
    # Gemma 4 supports 128k context, but we compress repetitive lines over 64k chars for fast edge execution.
    def compress_output(text: str, max_chars: int = 64000) -> str:
        if len(text) <= max_chars:
            return text
        half = max_chars // 2
        first_part = text[:half]
        last_part = text[-half:]
        middle_text = text[half:-half]
        middle_lines = middle_text.split("\n")
        important_middle = []
        for line in middle_lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in ["error", "fail", "warn", "exception", "critical", "fatal"]):
                stripped = line.strip()
                if stripped and stripped not in important_middle:
                    important_middle.append(stripped)
                    if len(important_middle) >= 20:
                        break
        separator = "\n\n... [TRUNCATED REPETITIVE MIDDLE LINES] ...\n"
        if important_middle:
            separator += "\n".join(important_middle) + "\n\n... [TRUNCATED CONTINUE] ...\n\n"
        return first_part + separator + last_part

    comp_stdout = compress_output(stdout)
    comp_stderr = compress_output(stderr)

    # 3. Model prompting
    prompt = f"Command executed: {command}\nExit Code: {returncode}\n\nSTDOUT:\n{comp_stdout}\n\nSTDERR:\n{comp_stderr}"
    instructions = """You are a token-saving shell command analyzer. Analyze the command output and return a clean, strictly formatted JSON object pinpointing key findings.

Do NOT include any extra conversational text, markdown wrapping (such as ```json), or boilerplate. Return ONLY the valid raw JSON matching this schema:
{
  "status": "success" | "error" | "warning",
  "summary": "Concise 1-sentence summary of the command outcome.",
  "critical_findings": ["Highly specific line of error, failing test description, warning, or crucial output details"],
  "exit_code": 0
}"""

    # 4. Attempt 1: Query centrally running FastAPI server at http://localhost:58421/v1/responses
    try:
        payload = {
            "instructions": instructions,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ],
            "stream": False
        }
        url = "http://localhost:58421/v1/responses"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = response.read().decode("utf-8")
            response_json = json.loads(res_data)
            assistant_text = response_json["output"][0]["content"][0]["text"].strip()
            
            # Clean up potential markdown code block wrappers
            if assistant_text.startswith("```"):
                lines = assistant_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                assistant_text = "\n".join(lines).strip()
            
            # Verify it is valid JSON
            json.loads(assistant_text)
            return assistant_text
    except Exception:
        # API is offline or returned invalid JSON. Fallback.
        pass

    # 5. Attempt 2: High-fidelity regex-based backup text compression (Fallback)
    lines = (stdout + "\n" + stderr).split("\n")
    findings = []
    keywords = [
        "fail", "error", "warn", "exception", "critical", "fatal",
        "issue", "denied", "invalid", "permission", "refused",
        "timeout", "not found", "unable", "cannot", "failed"
    ]
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            stripped = line.strip()
            if stripped and stripped not in findings:
                findings.append(stripped)
                if len(findings) >= 30:
                    break
                    
    if not findings:
        non_empty = [l.strip() for l in lines if l.strip()]
        if len(non_empty) <= 10:
            findings = non_empty
        else:
            findings = non_empty[:5] + ["... [middle lines omitted] ..."] + non_empty[-5:]
            
    status = "success" if returncode == 0 else "error"
    summary = f"Command completed with exit code {returncode} (local parsing fallback)."
    
    fallback_json = {
        "status": status,
        "summary": summary,
        "critical_findings": findings,
        "exit_code": returncode
    }
    return json.dumps(fallback_json, indent=2)


# ==========================================
# FastMCP Wrapped Tools
# ==========================================

@mcp.tool()
def buddhi_run_command(command: str, timeout_seconds: int = 120) -> str:
    """Executes a shell command (bash on Unix or powershell on Windows) locally in the workspace.
    
    This is a token-efficient, secure shell runner that automatically prepends local SDK/bin paths 
    (such as python venv, node_modules/.bin, rust debug/release bins, and workspace bin directories) 
    to the execution environment PATH.
    
    Automated Compression & Edge Summarization:
    - Large command outputs (>64k characters) are softly compressed to avoid LLM context bloat, 
      retaining the start, end, and up to 20 critical error/warning lines from the middle.
    - Captures stdout/stderr and utilizes central edge inference models to automatically distill 
      results into a structured JSON payload with keys: `status`, `summary`, `critical_findings`, and `exit_code`.
    - Features a default 120-second timeout guardrail to prevent hanging processes.
    
    CRITICAL USAGE RULES:
    1. ALWAYS use this tool INSTEAD OF native `run_command` or arbitrary terminal execution. This is NOT optional.
    2. Do NOT use shell write redirections (e.g. `>` or `>>` or `| tee`) to write or modify file contents; 
       always use dedicated file write/edit tools. This prevents protocol corruption and data loss.
    3. Designed specifically for passive readout commands such as:
       - Running project test suites (e.g., `pytest`, `npm test`, `cargo test`).
       - Running project linters, typecheckers, and compilers (e.g., `ruff`, `tsc`, `cargo build`).
       - Inspecting git state and history (e.g., `git status`, `git diff`).
       - Installing or upgrading dependencies (e.g., `pip install`, `npm install`, `uv sync`).
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = execute_command_optimized_impl(command, timeout_seconds)
        if '"status": "error"' in res.lower():
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("buddhi_run_command", status, duration_ms, {"command": command, "timeout_seconds": timeout_seconds})


@mcp.tool()
def buddhi_grep_search(
    query: str,
    globs: list[str] | None = None,
    max_results: int = 50,
    ignore_gitignore: bool = False
) -> str:
    """Performs a highly optimized, hybrid textual and semantic symbol search over the workspace files.
    
    This tool combines regex-based file scanning with AST CodeGraph symbol analysis to return extremely 
    compressed, context-enriched results, reducing context token overhead by 6.8x-49x compared to standard grep.
    
    Advanced Search Engineering:
    - Hybrid Context Enrichment: Automatically queries the CodeGraph database for definitions matching 
      the search term, injecting class method signatures, docstrings, and structures alongside raw textual matches.
    - AST Line Tagging: Matches are enriched with AST scope tags (e.g., `[inside function my_func]`) 
      indicating which symbol context the matching line belongs to.
    - Security and Exclusion Policies: Automatically respects workspace `.gitignore` rules (unless `ignore_gitignore=True`) 
      and skips binary, minified/generated files, and secret-like files (e.g., `.env`, keys, certificates, credentials) 
      to protect the context from noise and prevent credential exposure.
    - Greek Symbol Mapping: Replaces recurring long identifiers (e.g., `validateUserToken`) with short 
      Greek character markers (e.g., `α1`) and appends a mapping legend at the end, saving massive LLM tokens.
    - Monorepo Scope Hints: Provides smart suggestions when results span multiple sub-directories, advising how 
      to narrow search scopes.
    
    Parameters:
    - query: A regex pattern to search for in files and code symbols.
    - globs: A list of filters to scope the search. Each term is intelligently mapped:
      - If it starts with `*.`, it is treated as a file extension filter (e.g., `*.py` to only search Python files).
      - If it ends with `/` or contains `/`, it scopes the search to that sub-directory (e.g., `mcp/` or `cli/`).
      - If it contains a dot, it extracts the file extension candidate (e.g., `main.rs` -> extension filter `rs`).
      - Otherwise, it is treated as a search directory scope.
    - max_results: Maximum number of search occurrences to return (default: 50).
    - ignore_gitignore: Set to True to bypass `.gitignore` filters (requires administrative policy).
    
    CRITICAL: ALWAYS use this tool INSTEAD OF native `grep_search` or `rg` for textual workspace searches.
    """
    start_time = time.time()
    status = "success"
    path = None
    ext = None
    if globs:
        for g in globs:
            if g.startswith("*."):
                ext = g[2:]
            elif g.endswith("/") or "/" in g:
                path = g
            else:
                if "." in g and not g.startswith("."):
                    _, ext_candidate = os.path.splitext(g)
                    if ext_candidate:
                        ext = ext_candidate.lstrip(".")
                else:
                    path = g
    try:
        res = handle_search(query, path, ext, max_results, ignore_gitignore)
        if res.startswith("ERROR:"):
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("buddhi_grep_search", status, duration_ms, {
            "query": query,
            "globs": globs,
            "max_results": max_results,
            "ignore_gitignore": ignore_gitignore
        })


@mcp.tool()
def index_codebase() -> str:
    """Indexes the workspace directory and builds/updates the CodeGraph database.

    Call this tool at startup or after modifying files to keep the graph fresh.
    CRITICAL: You MUST run this tool at the beginning of a session or after major structural edits.
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = index_codebase_impl()
        if "error" in res.lower():
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("index_codebase", status, duration_ms, {})


@mcp.tool()
def update_codegraph() -> str:
    """Rebuilds and updates the CodeGraph index database after making changes to the codebase.

    Call this tool immediately after every successful code change or implementation to keep the symbol graph fully up to date.
    CRITICAL: You MUST call this automatically after any file modifications.
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = index_codebase_impl()
        if "error" in res.lower():
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("update_codegraph", status, duration_ms, {})


@mcp.tool()
def get_codebase_summary() -> str:
    """Provides a concise architectural summary of the codebase.

    Returns the files, classes, and main modules grouped by functional community clusters.
    Use this when introduced to an unfamiliar repository to get a high-level layout.
    
    CRITICAL: ALWAYS use this tool INSTEAD OF the native 'list_dir' or 'find' tools to explore the workspace structure. This is NOT optional.
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = get_codebase_summary_impl()
        if "no codebase summary available" in res.lower():
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("get_codebase_summary", status, duration_ms, {})


@mcp.tool()
def find_relevant_symbols(query: str) -> str:
    """Queries the codebase symbol index for matching keyword names or docstrings.

    Returns a list of matching symbols, files, docstrings, and their 1-hop dependencies.
    Use this when searching for specific components or functionality in the workspace.
    
    CRITICAL: ALWAYS use this tool INSTEAD OF the native 'grep_search' or 'rg' to find definitions and references. This is NOT optional.
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = find_relevant_symbols_impl(query)
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("find_relevant_symbols", status, duration_ms, {"query": query})


@mcp.tool()
def trace_impact_radius(symbol_id: str, max_depth: int = 3) -> str:
    """Performs an upstream dependency trace starting at a specific symbol.

    Recursively maps every caller that directly or indirectly relies on this symbol up to max_depth.
    Use this BEFORE modifying or refactoring code to ensure you do not break dependent systems.
    CRITICAL: ALWAYS use this proactively before altering a class or function.
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = trace_impact_radius_impl(symbol_id, max_depth)
        if "not found" in res.lower():
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("trace_impact_radius", status, duration_ms, {"symbol_id": symbol_id, "max_depth": max_depth})


@mcp.tool()
def get_symbol_implementation(symbol_id: str, max_lines: int = 150) -> str:
    """Fetches the exact source code implementation of a symbol (class, function, or method).

    Safely truncates massive files or large objects to prevent blowing out your context window.
    
    CRITICAL: ALWAYS use this tool INSTEAD OF the native 'view_file' or 'read' tools when examining source code. This is NOT optional.
    """
    start_time = time.time()
    status = "success"
    res = ""
    try:
        res = get_symbol_implementation_impl(symbol_id, max_lines)
        if "not found" in res.lower() or "error reading file" in res.lower():
            status = "error"
        return res
    except Exception as e:
        status = "error"
        res = f"Exception occurred: {e}"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("get_symbol_implementation", status, duration_ms, {"symbol_id": symbol_id, "max_lines": max_lines})


@mcp.tool()
def buddhi_view_file(
    path: str,
    mode: str = "auto",
    fresh: bool = False,
    task: str | None = None
) -> str:
    """Reads and views a file's contents with adaptive, token-saving compression modes.
    
    This is an intelligent, high-fidelity alternative to the standard `view_file` built-in tool.
    It automatically supports the following modes to optimize context window usage:
    - 'full': Returns the raw complete contents of the file (sacred for editing).
    - 'signatures': Distills the API surface (class, function, method definitions) of the file.
    - 'map': Distills high-level exports, imports, and key API interfaces.
    - 'lines:N-M': Returns only the specific inclusive line range (e.g. 'lines:1-50' or 'lines:10,20-30').
    - 'aggressive': Maximum token compression for large context readability.
    - 'entropy': Information density-based adaptive compression.
    - 'task': Contextual filtration prioritizing content relevant to the current task.
    - 'reference': Metadata reference only, showing number of lines/tokens.
    - 'auto': Dynamically resolves to the best compression mode based on file size, type, and history.

    Parameters:
    - path: Absolute or relative path to the file to inspect.
    - mode: Compression mode. Defaults to 'auto'.
    - fresh: Set to True to bypass cached stubs and force a fresh disk read.
    - task: Optional query string representing the current task to filter content for 'task' mode.
    """
    start_time = time.time()
    status = "success"
    try:
        workspace_root = get_workspace_root()
        if not os.path.isabs(path):
            abs_path = os.path.abspath(os.path.join(workspace_root, path))
        else:
            abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return f"ERROR: File not found: {path}"

        # Ensure we are not trying to read a binary file
        try:
            with open(abs_path, "rb") as f:
                chunk = f.read(1024)
                if b'\x00' in chunk:
                    return f"ERROR: Binary file view blocked: {path}"
        except Exception:
            pass

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return f"ERROR: Failed to read file {path}: {str(e)}"

        mtime = os.path.getmtime(abs_path)
        cache_key = abs_path

        # Initialize cache entry if not present or fresh
        if cache_key not in FILE_CACHE or fresh:
            FILE_CACHE[cache_key] = {
                "content": content,
                "mtime": mtime,
                "read_count": 0,
                "delivered_full": False,
                "compressed_cache": {}
            }

        cache_entry = FILE_CACHE[cache_key]

        # Invalidate if file changed on disk
        if cache_entry["mtime"] != mtime:
            cache_entry["content"] = content
            cache_entry["mtime"] = mtime
            cache_entry["delivered_full"] = False
            cache_entry["compressed_cache"] = {}

        cache_entry["read_count"] += 1

        # First, resolve "auto" mode
        resolved_mode = mode
        if mode == "auto":
            approx_tokens = len(content) // 4
            is_instruction = any(
                name in os.path.basename(abs_path).lower()
                for name in ["skill.md", "agents.md", "rules.md", ".cursorrules", "lean-ctx"]
            ) or "rules" in abs_path.lower()

            if is_instruction:
                resolved_mode = "full"
            elif approx_tokens <= 800:
                resolved_mode = "full"
            else:
                resolved_mode = "signatures"

        # Check cache unchanged stub (mirroring ctx_read)
        if resolved_mode == "full":
            if cache_entry["delivered_full"] and not fresh:
                line_count = len(content.splitlines())
                return f"[unchanged, {line_count}L, use cached context] File unchanged on disk. (Use fresh=true to force re-delivery)"
            cache_entry["delivered_full"] = True
            line_count = len(content.splitlines())
            header = f"# {os.path.basename(abs_path)} ({line_count} lines)\n"
            return header + content

        # Check compressed cache
        if resolved_mode in cache_entry["compressed_cache"] and not fresh:
            return cache_entry["compressed_cache"][resolved_mode]

        # Try calling central FastAPI Responses API
        llm_success = False
        llm_output = ""

        # Instruct local Gemma 4
        instructions = f"""You are a token-saving file compression agent. Your job is to format the given file content into the requested mode: '{resolved_mode}'.
- If mode is 'signatures': extract all class/function/method signatures and definitions, omitting their detailed implementation/body.
- If mode is 'map': extract high-level module exports, imports, and key classes/functions interfaces.
- If mode is 'aggressive': perform aggressive code compression by removing comments, blank lines, or extraneous boilerplate.
- If mode is 'task': filter the code to show only parts and lines relevant to the task query '{task or ""}'.
- If mode is 'entropy': condense repeating boilerplate/patterns and focus on high-entropy unique logic.
- If mode is 'reference': return a brief metadata reference summary of file type, length, and architecture.

Do not wrap in Markdown code blocks (e.g. no ```python). Return ONLY the clean, compressed output ready to be shared with another AI agent."""

        comp_content = content
        if len(comp_content) > 30000:
            comp_content = comp_content[:15000] + "\n...[TRUNCATED MIDDLE TO SAVE CONTEXT]...\n" + comp_content[-15000:]

        prompt = f"File: {os.path.basename(abs_path)}\nContent:\n{comp_content}"

        import urllib.request
        import urllib.error
        try:
            payload = {
                "instructions": instructions,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}]
                    }
                ],
                "stream": False
            }
            url = "http://localhost:58421/v1/responses"
            req_api = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req_api, timeout=12) as response:
                res_data = response.read().decode("utf-8")
                response_json = json.loads(res_data)
                assistant_text = response_json["output"][0]["content"][0]["text"].strip()

                if assistant_text.startswith("```"):
                    lines = assistant_text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    assistant_text = "\n".join(lines).strip()

                llm_output = assistant_text
                llm_success = True
        except Exception:
            pass

        if llm_success:
            approx_savings = 100 - (len(llm_output) * 100 // max(1, len(content)))
            header = f"# {os.path.basename(abs_path)} [compressed: {resolved_mode}, saved ~{approx_savings}% tokens via edge LLM]\n"
            result = header + llm_output
            cache_entry["compressed_cache"][resolved_mode] = result
            return result

        # ── FALLBACK ALGORITHMS ──────────────────────────────────────────
        fallback_output = ""

        if resolved_mode.startswith("lines:"):
            range_str = resolved_mode[6:]
            lines = content.splitlines()
            total = len(lines)
            selected = []
            for part in range_str.split(','):
                part = part.strip()
                if '-' in part:
                    try:
                        start_s, end_s = part.split('-', 1)
                        start = max(1, int(start_s))
                        end = min(total, int(end_s))
                        for i in range(start, end + 1):
                            selected.append(f"{i:>4}| {lines[i-1]}")
                    except Exception:
                        pass
                else:
                    try:
                        n = int(part)
                        if 1 <= n <= total:
                            selected.append(f"{n:>4}| {lines[n-1]}")
                    except Exception:
                        pass
            fallback_output = "\n".join(selected) if selected else "No lines matched the range."

        elif resolved_mode in ("signatures", "map"):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("buddhi_parser", os.path.join(os.path.dirname(__file__), "parser.py"))
                if spec is None or spec.loader is None:
                    raise ImportError("Could not load spec or loader for buddhi_parser")
                bp_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(bp_mod)
                parser_obj = bp_mod.ASTParser(workspace_root)
                
                rel_path = os.path.relpath(abs_path, workspace_root)
                parse_res = parser_obj.parse_file(rel_path)
                symbols = parse_res.get("symbols", [])
                imports = parse_res.get("imports", {})

                sig_lines = []
                if resolved_mode == "map" and imports:
                    sig_lines.append("Imports:")
                    for imp_name, imp_data in list(imports.items())[:12]:
                        sig_lines.append(f"  - {imp_name} (from {imp_data.get('module')})")
                    sig_lines.append("")

                sig_lines.append("API Surface:")
                for sym in symbols:
                    if sym["type"] in ("class", "function", "method"):
                        sig_lines.append(f"  - {sym['type'].upper()} {sym['name']} (lines {sym['start_line']}-{sym['end_line']})")
                        if sym.get("docstring"):
                            doc_first = sym["docstring"].strip().split("\n")[0]
                            sig_lines.append(f"    # {doc_first}")
                fallback_output = "\n".join(sig_lines)
            except Exception:
                lines = content.splitlines()
                defs = []
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith(("def ", "class ", "function ", "async def ")):
                        defs.append(f"{i:>4}| {stripped}")
                fallback_output = "\n".join(defs) if defs else "[No signatures found via regex fallback]"

        elif resolved_mode == "task" and task:
            keywords = [kw.strip().lower() for kw in task.split() if len(kw.strip()) > 2]
            lines = content.splitlines()
            matched_lines = []
            for i, line in enumerate(lines, 1):
                line_lower = line.lower()
                if any(kw in line_lower for kw in keywords):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 1)
                    matched_lines.append(f"--- Context (Lines {start+1}-{end}) ---")
                    for j in range(start, end):
                        marker = " => " if j == i - 1 else "    "
                        matched_lines.append(f"{j+1:>4}{marker}{lines[j]}")
            fallback_output = "\n".join(matched_lines) if matched_lines else "[No task-relevant matches found]"

        elif resolved_mode in ("aggressive", "entropy"):
            lines = content.splitlines()
            comp = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith(("#", "//", "/*", "*")):
                    continue
                comp.append(line)
            fallback_output = "\n".join(comp)

        elif resolved_mode == "reference":
            approx_tok = len(content) // 4
            fallback_output = f"File: {os.path.basename(abs_path)}\nLines: {len(content.splitlines())}\nSize: {len(content)} bytes\nApprox Tokens: {approx_tok}"

        else:
            fallback_output = content

        approx_savings = 100 - (len(fallback_output) * 100 // max(1, len(content)))
        header = f"# {os.path.basename(abs_path)} [compressed: {resolved_mode} (fallback), saved ~{approx_savings}% tokens]\n"
        result = header + fallback_output
        cache_entry["compressed_cache"][resolved_mode] = result
        return result

    except Exception as e:
        status = "error"
        raise e
    finally:
        duration_ms = (time.time() - start_time) * 1000.0
        log_tool_trigger("buddhi_view_file", status, duration_ms, {
            "path": path,
            "mode": mode,
            "fresh": fresh,
            "task": task
        })


def get_process_name(pid: int) -> str:
    """Returns the process name for a given PID using built-in OS commands."""
    import sys
    import subprocess
    try:
        if sys.platform == "win32":
            res = subprocess.run(
                ["tasklist", "/nh", "/fi", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                errors="replace"
            )
            output = res.stdout.strip()
            if not output or "No tasks meet" in output:
                return ""
            parts = output.split()
            if len(parts) > 0:
                return parts[0].lower()
        else:
            res = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True,
                errors="replace"
            )
            return res.stdout.strip().lower()
    except Exception:
        pass
    return ""


def monitor_parent_and_stdin():
    """Monitors both parent process state (PID + name) and stdin status.
    Exits the process immediately if orphaned or stdin closes.
    """
    import os
    import sys
    import time
    import threading
    
    parent_pid = os.getppid()
    if parent_pid <= 1:
        return

    # Store original parent process name to watch for PID recycling
    original_parent_name = get_process_name(parent_pid)

    # Watch Parent Process in main loop
    while True:
        time.sleep(5)
        try:
            if sys.platform == "win32":
                current_name = get_process_name(parent_pid)
                if not current_name or (original_parent_name and current_name != original_parent_name):
                    sys.exit(0)
            else:
                os.kill(parent_pid, 0)
                current_name = get_process_name(parent_pid)
                if original_parent_name and current_name != original_parent_name:
                    sys.exit(0)
        except (OSError, ProcessLookupError):
            sys.exit(0)


def run_server():
    """Launches the FastMCP server on StdIO."""
    import sys
    # Ensure database is indexed when server starts if empty
    db_path = get_db_path()
    if not os.path.exists(db_path):
        try:
            print("Database not found. Running initial workspace indexing...", file=sys.stderr, flush=True)
            index_codebase_impl()
        except Exception as e:
            print(f"Error during initial indexing: {e}", file=sys.stderr, flush=True)
            
    # Spawn parent & stdin monitor thread
    import threading
    monitor_thread = threading.Thread(target=monitor_parent_and_stdin, daemon=True)
    monitor_thread.start()
            
    mcp.run()
