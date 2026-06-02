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

    hook_parser = subparsers.add_parser("hook", help="Run a named hook handler (used by hooks.json)")
    hook_parser.add_argument(
        "name",
        choices=["gate-io", "pre-invoke"],
        help="Which hook to run",
    )

    metrics_parser = subparsers.add_parser("metrics", help="Show tool usage metrics and token savings")
    metrics_parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    metrics_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    metrics_parser.add_argument("--reset", action="store_true", help="Clear all metrics data")

    # AI command
    subparsers.add_parser("ai", help="Launch the interactive TUI Chat Interface")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the Buddhi API server (Gemma 4 E4B)")
    server_parser.add_argument("--verbose", action="store_true", help="Run the server in the foreground and show logs")

    # Shutdown command
    subparsers.add_parser("shutdown", help="Stop the background Buddhi API server")

    args = parser.parse_args()

    if args.command == "init":
        handle_init(args)
    elif args.command == "hook":
        if args.name == "gate-io":
            from buddhi_ai.hooks.gate_io import main as hook_main
        elif args.name == "pre-invoke":
            from buddhi_ai.hooks.pre_invoke import main as hook_main
        hook_main()
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


if __name__ == "__main__":
    main()
