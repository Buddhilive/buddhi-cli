import os
import sys


def get_model_target_dir():
    return os.path.join(os.path.expanduser("~"), ".buddhi", "models")


def setup_model():
    """Downloads the model required for inference."""
    from huggingface_hub import hf_hub_download

    target_dir = get_model_target_dir()
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")

    if os.path.exists(model_path):
        print("Model already exists at:", model_path)
    else:
        print("Downloading model from HuggingFace...", flush=True)
        os.makedirs(target_dir, exist_ok=True)
        hf_hub_download(
            repo_id="litert-community/gemma-4-E4B-it-litert-lm",
            filename="gemma-4-E4B-it.litertlm",
            local_dir=target_dir,
        )
        print("Model downloaded successfully!", flush=True)

    # Pre-generate XNNPack cache if possible
    try:
        import litert_lm
        print("Pre-generating XNNPack compilation cache (this might take a few seconds)...", flush=True)
        engine = litert_lm.Engine(model_path)
        with engine:
            pass
        print("XNNPack compilation cache pre-generated successfully!", flush=True)
    except Exception as e:
        print(f"Note: XNNPack cache will be generated automatically on first inference. (Detail: {e})", flush=True)


def init_workspace():
    """Initializes the current workspace by writing AGENTS.md, .agent/mcp_config.json, and indexing the codebase."""
    cwd = os.getcwd()
    
    # 1. Update/Create AGENTS.md
    agents_path = os.path.join(cwd, "AGENTS.md")
    
    buddhi_mcp_instructions = """<!-- buddhi-mcp-owned: buddhi-ai v1 -->
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
| `index_codebase()` | *None* | Updates the SQLite AST & Call Graph database. Run this at the start of a session or after major edits to ensure symbol synchronization. |
| `execute_command_optimized(command)` | `run_command` / `Shell` / `ctx_shell` | Executes shell commands locally and passes stdout/stderr to local Gemma 4 model (via centralized FastAPI server http://localhost:58421/v1/responses or fallback), producing a compact structured JSON pinpointing successes, errors, and warnings to save substantial tokens. |

## Recommended Workflow:
1. **Startup (Orient)**: Run `get_codebase_summary()` to understand the functional modules, key classes, and files in the repository.
2. **Search (Locate)**: Use `find_relevant_symbols(query: "...")` to find exact definitions and their immediately connected symbols.
3. **Inspect (Analyze)**: Call `get_symbol_implementation(symbol_id: "...")` to read a symbol's implementation. The model-safety guardrail ensures you don't blow out the context window.
4. **Refactor Guard (Safety)**: Before changing a function, class, or method, run `trace_impact_radius(symbol_id: "...")` to trace all upstream files/symbols that call or depend on it. This ensures zero regression!
5. **Sync (Refresh)**: After making changes, call `index_codebase()` to rebuild the graph.
6. **Optimized Execution**: For running builds, tests, or diagnostics, prefer `execute_command_optimized(command: "...")` to drastically compress terminal output and avoid wasting assistant tokens.

<!-- /buddhi-mcp -->"""
    
    import re
    if os.path.exists(agents_path):
        try:
            with open(agents_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading AGENTS.md: {e}")
            return
        
        # Check if block already exists
        pattern = r"<!-- buddhi-mcp-owned:.*?<!-- /buddhi-mcp -->"
        if re.search(pattern, content, re.DOTALL):
            # Replace existing block
            updated_content = re.sub(pattern, buddhi_mcp_instructions.strip(), content, flags=re.DOTALL)
            print("Updating existing buddhi instructions in AGENTS.md...")
        else:
            # Append block
            updated_content = content.rstrip() + "\n\n" + buddhi_mcp_instructions
            print("Appending buddhi instructions to existing AGENTS.md...")
    else:
        updated_content = buddhi_mcp_instructions
        print("Creating new AGENTS.md with buddhi instructions...")
        
    try:
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"Successfully wrote AGENTS.md at: {agents_path}")
    except Exception as e:
        print(f"Error writing to AGENTS.md: {e}")
        return

    # 2. Update/Create .agent/mcp_config.json
    agent_dir = os.path.join(cwd, ".agent")
    mcp_path = os.path.join(agent_dir, "mcp_config.json")
    
    os.makedirs(agent_dir, exist_ok=True)
    
    mcp_config_data = {
        "mcpServers": {
            "buddhi-mcp": {
                "command": "buddhi",
                "args": ["mcp"]
            }
        }
    }
    
    import json
    if os.path.exists(mcp_path):
        try:
            with open(mcp_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
                clean_raw = re.sub(r"//.*", "", raw_data)
                data = json.loads(clean_raw)
        except Exception as e:
            print(f"Error parsing existing mcp_config.json: {e}. Reinitializing config...")
            data = {"mcpServers": {}}
            
        if "mcpServers" not in data:
            data["mcpServers"] = {}
            
        # Update/insert buddhi-mcp server config
        data["mcpServers"]["buddhi-mcp"] = {
            "command": "buddhi",
            "args": ["mcp"]
        }
        print("Updating existing .agent/mcp_config.json...")
    else:
        data = mcp_config_data
        print("Creating new .agent/mcp_config.json...")
        
    try:
        with open(mcp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Successfully wrote .agent/mcp_config.json at: {mcp_path}")
    except Exception as e:
        print(f"Error writing to .agent/mcp_config.json: {e}")
        return

    # 3. Trigger initial AST Indexing
    print("Initializing AST codebase indexing & call graph compilation...")
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mcp_dir = os.path.join(base_dir, "mcp")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        from server import index_codebase_impl
        indexing_result = index_codebase_impl(workspace_root=cwd)
        print(f"Indexing Complete: {indexing_result}")
    except Exception as e:
        print(f"Error during codebase indexing: {e}")
        print("Please run 'buddhi mcp' manually to ensure symbol DB is initialized.")

    print("\nBuddhi MCP successfully initialized for Antigravity!")


def start(host="127.0.0.1", port=58421, ui_port=58422, no_browser=False):
    """Starts the FastAPI server and Streamlit chat UI concurrently."""
    target_dir = get_model_target_dir()
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")

    if not os.path.exists(model_path):
        print("Warning: Model not found. You may need to run 'buddhi setup' first.")

    import threading
    import subprocess
    import sys
    import uvicorn
    import time

    # Configure and start FastAPI via uvicorn in a daemon thread
    config = uvicorn.Config("server.main:app", host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    
    def run_server():
        try:
            server.run()
        except SystemExit:
            pass

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Build command to run Streamlit in headless mode to bypass interactive prompts (like email registration)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ui_app_path = os.path.join(base_dir, "ui", "app.py")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        ui_app_path,
        "--server.port",
        str(ui_port),
        "--server.address",
        host,
        "--server.headless",
        "true",
    ]

    # Set dynamic environment variables for Streamlit backend connection
    env = os.environ.copy()
    env["BUDDHI_BACKEND_HOST"] = host
    env["BUDDHI_BACKEND_PORT"] = str(port)

    print(f"\nStarting backend server at http://{host}:{port}", flush=True)
    print(f"Starting Streamlit chat UI at http://{host}:{ui_port}...", flush=True)

    try:
        process = subprocess.Popen(cmd, env=env)
        
        # Open browser automatically if not explicitly disabled by the user
        if not no_browser:
            import webbrowser
            def open_browser():
                time.sleep(2.0)
                if process.poll() is None:
                    webbrowser.open(f"http://{host}:{ui_port}")
            threading.Thread(target=open_browser, daemon=True).start()

        try:
            # Monitor the running process and fail fast if uvicorn fails to bind or exits
            while process.poll() is None:
                if server.should_exit or not server_thread.is_alive():
                    print("\nBackend server stopped or failed to bind. Shutting down Streamlit...", flush=True)
                    process.terminate()
                    process.wait()
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nShutting down Buddhi AI live servers...", flush=True)
            process.terminate()
            process.wait()
            server.should_exit = True
    except Exception as e:
        print(f"Error running Streamlit UI: {e}", flush=True)


def cli():
    """CLI entry point for the buddhi command."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Buddhi AI — Local LLM inference.\n"
            "Run 'buddhi live' to launch the Streamlit chat UI."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # setup subcommand
    subparsers.add_parser(
        "setup",
        help="Download the required local edge inference model.",
    )

    # live subcommand — browser-based Streamlit UI
    live_parser = subparsers.add_parser(
        "live",
        help="Start the FastAPI backend and serve the Streamlit chat UI in a browser.",
    )
    live_parser.add_argument(
        "--port", type=int, default=58421,
        help="Port to run the backend FastAPI server on (default: 58421)",
    )
    live_parser.add_argument(
        "--ui-port", type=int, default=58422,
        help="Port to run the Streamlit UI on (default: 58422)",
    )
    live_parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)",
    )
    live_parser.add_argument(
        "--no-browser", action="store_true",
        help="Bypass automatic opening of the system browser",
    )

    # mcp subcommand — StdIO transport FastMCP server
    subparsers.add_parser(
        "mcp",
        help="Start the CodeGraph Model Context Protocol (MCP) server over StdIO transport.",
    )

    # init subcommand — Workspace configuration
    subparsers.add_parser(
        "init",
        help="Initialize Buddhi MCP settings and instructions (AGENTS.md and .agent/mcp_config.json) in the current workspace.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        setup_model()
    elif args.command == "live":
        start(
            host=args.host,
            port=args.port,
            ui_port=args.ui_port,
            no_browser=args.no_browser
        )
    elif args.command == "mcp":
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mcp_dir = os.path.join(base_dir, "mcp")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        import server
        server.run_server()
    elif args.command == "init":
        init_workspace()
    else:
        # Default: no subcommand → show help
        parser.print_help()


if __name__ == "__main__":
    cli()

