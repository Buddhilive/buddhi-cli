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

        print(
            "Pre-generating XNNPack compilation cache (this might take a few seconds)...",
            flush=True,
        )
        engine = litert_lm.Engine(model_path)
        with engine:
            pass
        print("XNNPack compilation cache pre-generated successfully!", flush=True)
    except Exception as e:
        print(
            f"Note: XNNPack cache will be generated automatically on first inference. (Detail: {e})",
            flush=True,
        )


def load_buddhi_mcp_server():
    """Loads the local buddhi-ai mcp/server.py module using importlib to prevent naming collisions with the official mcp library."""
    import importlib.util

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mcp_dir = os.path.join(base_dir, "mcp")
    mcp_server_path = os.path.join(mcp_dir, "server.py")

    # Ensure mcp_dir is in sys.path so that server.py can import db, indexer, parser, graph
    # Use append instead of insert(0, ...) to prevent shadowing standard library modules (like types)
    if mcp_dir not in sys.path:
        sys.path.append(mcp_dir)

    # Unit testing compatibility check:
    # If 'server' is in sys.modules (e.g. injected/mocked by unittest), and has the index_codebase_impl attribute, return it.
    if "server" in sys.modules and hasattr(
        sys.modules["server"], "index_codebase_impl"
    ):
        return sys.modules["server"]

    module_name = "buddhi_mcp_server"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, mcp_server_path)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load spec for Buddhi MCP server at {mcp_server_path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def init_workspace(workspace_root=None):
    """Initializes the current workspace by writing .agent/mcp_config.json, separate tool rule files, and indexing the codebase."""
    if workspace_root:
        cwd = os.path.abspath(workspace_root)
    else:
        cwd = os.getcwd()

    # 1. Update/Create .agent/mcp_config.json
    agent_dir = os.path.join(cwd, ".agent")
    mcp_path = os.path.join(agent_dir, "mcp_config.json")

    os.makedirs(agent_dir, exist_ok=True)

    mcp_config_data = {
        "mcpServers": {
            "buddhi-mcp": {
                "command": "buddhi",
                "args": ["mcp"],
                "env": {"BUDDHI_WORKSPACE_ROOT": cwd},
            }
        }
    }

    import re
    import json

    if os.path.exists(mcp_path):
        try:
            with open(mcp_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
                clean_raw = re.sub(r"//.*", "", raw_data)
                data = json.loads(clean_raw)
        except Exception as e:
            print(
                f"Error parsing existing mcp_config.json: {e}. Reinitializing config..."
            )
            data = {"mcpServers": {}}

        if "mcpServers" not in data:
            data["mcpServers"] = {}

        # Update/insert buddhi-mcp server config
        data["mcpServers"]["buddhi-mcp"] = {
            "command": "buddhi",
            "args": ["mcp"],
            "env": {"BUDDHI_WORKSPACE_ROOT": cwd},
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

    # 2. Create separate tool rule files inside .agent/rules/
    rules_dir = os.path.join(cwd, ".agent", "rules")
    os.makedirs(rules_dir, exist_ok=True)

    grep_search_rule_path = os.path.join(rules_dir, "buddhi-grep-search.md")
    run_command_rule_path = os.path.join(rules_dir, "buddhi-run-command.md")
    view_file_rule_path = os.path.join(rules_dir, "buddhi-view-file.md")

    grep_search_rule_content = """---
activation: always-on
---
# Core Tool Execution Policy

1. The built-in tool `grep_search` is deprecated and disabled in this environment.
2. For all text-matching, regex searches, or code querying tasks, you MUST exclusively call the MCP tool `buddhi_grep_search`.
3. When calling `buddhi_grep_search`, inspect its schema parameters carefully:
   - Pass the search string into the `query` parameter (do not use `pattern`).
   - Pass directory filters into the `globs` array parameter."""

    run_command_rule_content = """---
activation: always-on
---
# Core Tool Execution Policy

1. The built-in shell execution tool `run_command` are deprecated and disabled in this environment.
2. For all shell command execution, terminal commands, compilation, building, running tests, or diagnostics, you MUST exclusively call the MCP tool `buddhi_run_command`.
3. When calling `buddhi_run_command`, inspect its schema parameters carefully:
   - Pass the shell command into the `command` parameter.
   - Adjust `timeout_seconds` if you expect a long-running command."""

    view_file_rule_content = """---
activation: always-on
---
# Core Tool Execution Policy

1. The built-in tool `view_file` is deprecated and disabled in this environment.
2. For all file reading, file viewing, and content inspection, you MUST exclusively call the MCP tool `buddhi_view_file`.
3. When calling `buddhi_view_file`, inspect its schema parameters carefully:
   - Pass the file path into the `path` parameter.
   - Pass the query/intent details into the `task` parameter to dynamically optimize token usage.
   - Specify `mode` (e.g. `auto`, `full`, `signatures`, `map`, `lines:1-100`) as appropriate to save context window tokens."""

    try:
        with open(grep_search_rule_path, "w", encoding="utf-8") as f:
            f.write(grep_search_rule_content)
        print(f"Successfully wrote buddhi-grep-search.md at: {grep_search_rule_path}")
    except Exception as e:
        print(f"Error writing to buddhi-grep-search.md: {e}")
        return

    try:
        with open(run_command_rule_path, "w", encoding="utf-8") as f:
            f.write(run_command_rule_content)
        print(f"Successfully wrote buddhi-run-command.md at: {run_command_rule_path}")
    except Exception as e:
        print(f"Error writing to buddhi-run-command.md: {e}")
        return

    try:
        with open(view_file_rule_path, "w", encoding="utf-8") as f:
            f.write(view_file_rule_content)
        print(f"Successfully wrote buddhi-view-file.md at: {view_file_rule_path}")
    except Exception as e:
        print(f"Error writing to buddhi-view-file.md: {e}")
        return

    # 3. Create .buddhi/.gitignore
    buddhi_dir = os.path.join(cwd, ".buddhi")
    os.makedirs(buddhi_dir, exist_ok=True)
    gitignore_path = os.path.join(buddhi_dir, ".gitignore")
    try:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("# Automatically created by buddhi.\n*\n")
        print(f"Successfully wrote .buddhi/.gitignore at: {gitignore_path}")
    except Exception as e:
        print(f"Error writing to .buddhi/.gitignore: {e}")

    # 4. Trigger initial AST Indexing
    print("Initializing AST codebase indexing & call graph compilation...")
    try:
        buddhi_mcp_server = load_buddhi_mcp_server()
        indexing_result = buddhi_mcp_server.index_codebase_impl(workspace_root=cwd)
        print(f"Indexing Complete: {indexing_result}")
    except Exception as e:
        print(f"Error during codebase indexing: {e}")
        print("Please run 'buddhi mcp' manually to ensure symbol DB is initialized.")

    print("\nBuddhi MCP successfully initialized for Antigravity!")


def start(
    backend_host="127.0.0.1",
    backend_port=58421,
    ui_host="127.0.0.1",
    ui_port=58422,
    no_browser=False,
):
    """Starts the Streamlit chat UI."""
    import subprocess
    import sys
    import time
    import threading

    print(
        "\nNote: The Streamlit chat UI requires the Buddhi backend server to be running.",
        flush=True,
    )
    print("      Make sure you run 'buddhi server' centrally.", flush=True)

    # Build command to run Streamlit in headless mode to bypass interactive prompts (like email registration)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ui_app_path = os.path.join(base_dir, "ui", "app.py")

    # Auto-detect workspace virtualenv Python to load installed packages correctly
    python_exe = sys.executable
    cwd = os.getcwd()
    if sys.platform == "win32":
        venv_candidate = os.path.join(cwd, ".venv", "Scripts", "python.exe")
    else:
        venv_candidate = os.path.join(cwd, ".venv", "bin", "python")

    if os.path.exists(venv_candidate):
        python_exe = venv_candidate
        print(f"Using workspace virtualenv interpreter: {python_exe}", flush=True)

    cmd = [
        python_exe,
        "-m",
        "streamlit",
        "run",
        ui_app_path,
        "--server.port",
        str(ui_port),
        "--server.address",
        ui_host,
        "--server.headless",
        "true",
    ]

    # Set dynamic environment variables for Streamlit backend connection
    env = os.environ.copy()
    env["BUDDHI_BACKEND_HOST"] = backend_host
    env["BUDDHI_BACKEND_PORT"] = str(backend_port)

    # Ensure the root project directory is in PYTHONPATH so 'ui' module can be found
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{base_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = base_dir

    print(f"\nStarting Streamlit chat UI at http://{ui_host}:{ui_port}...", flush=True)

    try:
        process = subprocess.Popen(cmd, env=env)

        # Open browser automatically if not explicitly disabled by the user
        if not no_browser:
            import webbrowser

            def open_browser():
                time.sleep(2.0)
                if process.poll() is None:
                    webbrowser.open(f"http://{ui_host}:{ui_port}")

            threading.Thread(target=open_browser, daemon=True).start()

        try:
            # Monitor the running process
            while process.poll() is None:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nShutting down Buddhi AI Streamlit UI...", flush=True)
            process.terminate()
            process.wait()
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
        "--backend-port",
        type=int,
        default=58421,
        help="Port of the backend FastAPI server to connect to (default: 58421)",
    )
    live_parser.add_argument(
        "--backend-host",
        type=str,
        default="127.0.0.1",
        help="Host address of the backend server (default: 127.0.0.1)",
    )
    live_parser.add_argument(
        "--ui-port",
        type=int,
        default=58422,
        help="Port to run the Streamlit UI on (default: 58422)",
    )
    live_parser.add_argument(
        "--ui-host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind the Streamlit UI to (default: 127.0.0.1)",
    )
    live_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Bypass automatic opening of the system browser",
    )

    # mcp subcommand — StdIO transport FastMCP server
    subparsers.add_parser(
        "mcp",
        help="Start the CodeGraph Model Context Protocol (MCP) server over StdIO transport.",
    )

    # init subcommand — Workspace configuration
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize Buddhi MCP settings and instructions (AGENTS.md and .agent/mcp_config.json) in the current workspace.",
    )
    init_parser.add_argument(
        "--workspace-root",
        type=str,
        default=None,
        help="Absolute path of the workspace root. Defaults to the current working directory.",
    )

    # update subcommand — Explicitly update CodeGraph
    subparsers.add_parser(
        "update",
        help="Explicitly scan the workspace and update the CodeGraph database.",
    )

    # benchmark subcommand — Quantitative Benchmark Suite
    subparsers.add_parser(
        "benchmark",
        help="Run the quantitative benchmark suite to calculate exact token savings across the current codebase.",
    )

    # server subcommand — Start FastAPI backend only
    server_parser = subparsers.add_parser(
        "server",
        help="Start the FastAPI backend server only.",
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=58421,
        help="Port to run the backend FastAPI server on (default: 58421)",
    )
    server_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    if args.command == "setup":
        setup_model()
    elif args.command == "live":
        start(
            backend_host=args.backend_host,
            backend_port=args.backend_port,
            ui_host=args.ui_host,
            ui_port=args.ui_port,
            no_browser=args.no_browser,
        )
    elif args.command == "mcp":
        try:
            buddhi_mcp_server = load_buddhi_mcp_server()
            buddhi_mcp_server.run_server()
        except Exception as e:
            print(f"Error starting MCP server: {e}")
    elif args.command == "init":
        init_workspace(workspace_root=args.workspace_root)
    elif args.command == "update":
        print("Explicitly triggering AST indexing and call graph compilation...")
        try:
            cwd = os.getcwd()
            buddhi_mcp_server = load_buddhi_mcp_server()
            indexing_result = buddhi_mcp_server.index_codebase_impl(workspace_root=cwd)
            print(f"Update Complete: {indexing_result}")
        except Exception as e:
            print(f"Error during codebase update: {e}")
    elif args.command == "benchmark":
        from cli.metrics import run_benchmark

        run_benchmark()
    elif args.command == "server":
        target_dir = get_model_target_dir()
        model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")
        if not os.path.exists(model_path):
            print("Warning: Model not found. You may need to run 'buddhi setup' first.")

        import uvicorn

        print(
            f"\nStarting backend server at http://{args.host}:{args.port}...",
            flush=True,
        )
        try:
            uvicorn.run(
                "server.main:app", host=args.host, port=args.port, log_level="info"
            )
        except Exception as e:
            print(f"Error starting backend server: {e}", flush=True)
    else:
        # Default: no subcommand → show help
        parser.print_help()


if __name__ == "__main__":
    cli()
