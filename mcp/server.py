import os
from mcp.server.fastmcp import FastMCP
from db import CodeGraphDB, get_db_path
from indexer import CodeIndexer

# Initialize FastMCP Server
mcp = FastMCP("CodeGraph")


# ==========================================
# Core Reusable Implementation Methods
# ==========================================

def index_codebase_impl(workspace_root=None):
    """Indexes/re-indexes the codebase files and rebuilds the sqlite graph database."""
    if not workspace_root:
        workspace_root = os.getcwd()
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
        workspace_root = os.getcwd()

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


def execute_command_optimized_impl(command: str) -> str:
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

    # 1. OS-specific shell command runner
    try:
        if sys.platform == "win32":
            # Using powershell explicitly provides a more reliable environment on Windows than standard cmd
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            stdout, stderr, returncode = res.stdout, res.stderr, res.returncode
        else:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            stdout, stderr, returncode = res.stdout, res.stderr, res.returncode
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

    # 5. Attempt 2: Standalone local litert_lm.Engine direct invocation
    try:
        model_path = os.path.join(os.path.expanduser("~"), ".buddhi", "models", "gemma-4-E4B-it.litertlm")
        if os.path.exists(model_path):
            import litert_lm
            engine = litert_lm.Engine(model_path)
            with engine:
                messages = [
                    {"role": "system", "content": [{"type": "text", "text": instructions}]},
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ]
                with engine.create_conversation(messages=messages[:-1]) as conversation:
                    response_obj = conversation.send_message(prompt) if hasattr(conversation, 'send_message') else conversation.send_message_async(prompt)
                    
                    response_text = ""
                    if hasattr(response_obj, '__iter__') and not isinstance(response_obj, (dict, str)):
                        for chunk in response_obj:
                            if isinstance(chunk, str):
                                response_text += chunk
                            elif isinstance(chunk, dict):
                                c = chunk.get("content", "")
                                if isinstance(c, list) and len(c) > 0:
                                    response_text += c[0].get("text", "") if isinstance(c[0], dict) else str(c[0])
                                elif isinstance(c, str):
                                    response_text += c
                    else:
                        if isinstance(response_obj, str):
                            response_text = response_obj
                        elif isinstance(response_obj, dict):
                            c = response_obj.get("content", "")
                            if isinstance(c, list) and len(c) > 0:
                                response_text = c[0].get("text", "") if isinstance(c[0], dict) else str(c[0])
                            elif isinstance(c, str):
                                response_text = c
                        else:
                            response_text = getattr(response_obj, "text", str(response_obj))
                            
                    response_text = response_text.strip()
                    if response_text.startswith("```"):
                        lines = response_text.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        response_text = "\n".join(lines).strip()
                    
                    # Verify it's valid JSON
                    json.loads(response_text)
                    return response_text
    except Exception:
        # Fallback to smart regex
        pass

    # 6. Attempt 3: High-fidelity regex-based backup text compression
    lines = (stdout + "\n" + stderr).split("\n")
    findings = []
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["error", "fail", "warn", "exception", "critical", "fatal", "issue", "denied"]):
            stripped = line.strip()
            if stripped and stripped not in findings:
                findings.append(stripped)
                if len(findings) >= 15:
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
def execute_command_optimized(command: str) -> str:
    """Executes a shell command (bash or powershell) locally, processes the stdout/stderr
    using local Gemma 4 edge inference to identify key successes or failures,
    and returns a compact, token-saving structured JSON summary.
    """
    return execute_command_optimized_impl(command)


@mcp.tool()
def index_codebase() -> str:
    """Indexes the workspace directory and builds/updates the CodeGraph database.

    Call this tool at startup or after modifying files to keep the graph fresh.
    """
    return index_codebase_impl()


@mcp.tool()
def update_codegraph() -> str:
    """Rebuilds and updates the CodeGraph index database after making changes to the codebase.

    Call this tool immediately after every successful code change or implementation to keep the symbol graph fully up to date.
    """
    return index_codebase_impl()


@mcp.tool()
def get_codebase_summary() -> str:
    """Provides a concise architectural summary of the codebase.

    Returns the files, classes, and main modules grouped by functional community clusters.
    Use this when introduced to an unfamiliar repository to get a high-level layout.
    """
    return get_codebase_summary_impl()


@mcp.tool()
def find_relevant_symbols(query: str) -> str:
    """Queries the codebase symbol index for matching keyword names or docstrings.

    Returns a list of matching symbols, files, docstrings, and their 1-hop dependencies.
    Use this when searching for specific components or functionality in the workspace.
    """
    return find_relevant_symbols_impl(query)


@mcp.tool()
def trace_impact_radius(symbol_id: str, max_depth: int = 3) -> str:
    """Performs an upstream dependency trace starting at a specific symbol.

    Recursively maps every caller that directly or indirectly relies on this symbol up to max_depth.
    Use this BEFORE modifying or refactoring code to ensure you do not break dependent systems.
    """
    return trace_impact_radius_impl(symbol_id, max_depth)


@mcp.tool()
def get_symbol_implementation(symbol_id: str, max_lines: int = 150) -> str:
    """Fetches the exact source code implementation of a symbol (class, function, or method).

    Safely truncates massive files or large objects to prevent blowing out your context window.
    """
    return get_symbol_implementation_impl(symbol_id, max_lines)


def run_server():
    """Launches the FastMCP server on StdIO."""
    # Ensure database is indexed when server starts if empty
    db_path = get_db_path()
    if not os.path.exists(db_path):
        try:
            print("Database not found. Running initial workspace indexing...", flush=True)
            index_codebase_impl()
        except Exception as e:
            print(f"Error during initial indexing: {e}", flush=True)
            
    mcp.run()
