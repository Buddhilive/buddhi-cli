import os
import sys

def get_model_target_dir():
    # The 'server' folder is adjacent to the 'cli' folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "server", "static", "model")

def setup_model():
    """
    Downloads the model required for inference.
    """
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
        local_dir=target_dir
    )
    print("Model downloaded successfully!", flush=True)

def start(host="127.0.0.1", port=58421, no_browser=False):
    """
    Starts the server.
    """
    target_dir = get_model_target_dir()
    model_path = os.path.join(target_dir, "gemma-4-E4B-it.litertlm")
    
    if not os.path.exists(model_path):
        print("Warning: Model not found. You may need to run 'buddhi setup' first.")

    import uvicorn
    import threading
    import webbrowser
    import time

    def open_browser():
        time.sleep(1.5)
        url = f"http://{host}:{port}"
        print(f"\nBuddhi AI is live! Opening browser at {url} ...", flush=True)
        webbrowser.open(url)

    if not no_browser:
        threading.Thread(target=open_browser, daemon=True).start()
    else:
        print(f"\nBuddhi AI is live! Access it at http://{host}:{port}", flush=True)

    uvicorn.run("server.main:app", host=host, port=port)

def cli():
    """
    CLI entry point.
    """
    import argparse
    parser = argparse.ArgumentParser(
        description="Buddhi AI: Unified CLI tool for local LLM inference and Chat UI."
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # setup subcommand
    subparsers.add_parser("setup", help="Download the required local edge inference model.")

    # live subcommand
    live_parser = subparsers.add_parser("live", help="Start the FastAPI backend and serve Svelte UI.")
    live_parser.add_argument("--port", type=int, default=58421, help="Port to run the server on (default: 58421)")
    live_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    live_parser.add_argument("--no-browser", action="store_true", help="Bypass automatic opening of the system browser")

    args = parser.parse_args()

    if args.command == "setup":
        setup_model()
    elif args.command == "live":
        start(host=args.host, port=args.port, no_browser=args.no_browser)
    else:
        # Default behavior when no subcommand is specified (backward compatibility)
        start()

if __name__ == "__main__":
    cli()
