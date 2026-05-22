import os
import sys


def get_model_target_dir():
    # The 'server' folder is adjacent to the 'cli' folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "server", "static", "model")


def setup_model():
    """Downloads the model required for inference."""
    from huggingface_hub import hf_hub_download

    target_dir = get_model_target_dir()
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")

    if os.path.exists(model_path):
        print("Model already exists at:", model_path)
        return

    print("Downloading model from HuggingFace...", flush=True)
    os.makedirs(target_dir, exist_ok=True)
    hf_hub_download(
        repo_id="litert-community/gemma-4-E4B-it-litert-lm",
        filename="gemma-4-E4B-it.litertlm",
        local_dir=target_dir,
    )
    print("Model downloaded successfully!", flush=True)


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
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "ui/app.py",
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
    else:
        # Default: no subcommand → show help
        parser.print_help()


if __name__ == "__main__":
    cli()

