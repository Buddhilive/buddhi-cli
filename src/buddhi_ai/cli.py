import argparse
from buddhi_ai.commands.init_cmd import handle_init
from buddhi_ai.commands.metrics_cmd import handle_metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="buddhi",
        description="buddhi-ai: A CLI tool to map structural entities and filter boilerplate in your codebase.",
    )

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize and scan the code workspace"
    )
    init_parser.add_argument(
        "--entropy-threshold",
        type=float,
        default=3.0,
        help="Shannon entropy threshold for filtering boilerplate lines (default: 3.0)",
    )


    metrics_parser = subparsers.add_parser("metrics", help="Show tool usage metrics and token savings")
    metrics_parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    metrics_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    metrics_parser.add_argument("--reset", action="store_true", help="Clear all metrics data")

    # AI command
    ai_parser = subparsers.add_parser("ai", help="Launch the interactive TUI Chat Interface")
    ai_parser.add_argument("--host", type=str, default="127.0.0.1", help="API server host (default: 127.0.0.1)")
    ai_parser.add_argument("--port", type=int, default=54321, help="API server port (default: 54321)")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the Buddhi API server (Gemma 4 E4B)")
    server_parser.add_argument("--verbose", action="store_true", help="Run the server in the foreground and show logs")

    # Shutdown command
    subparsers.add_parser("shutdown", help="Stop the background Buddhi API server")

    # Setup command
    subparsers.add_parser("setup", help="Download and prepare the Gemma 4 E4B model")

    args = parser.parse_args()

    if args.command == "init":
        handle_init(args)
    elif args.command == "metrics":
        handle_metrics(args)
    elif args.command == "ai":
        from buddhi_ai.commands.ai_cmd import handle_ai
        handle_ai(args)
    elif args.command == "server":
        from buddhi_ai.commands.server_cmd import handle_server
        handle_server(args)
    elif args.command == "shutdown":
        from buddhi_ai.commands.shutdown_cmd import handle_shutdown
        handle_shutdown(args)
    elif args.command == "setup":
        from buddhi_ai.commands.setup_cmd import handle_setup
        handle_setup(args)

if __name__ == "__main__":
    main()
