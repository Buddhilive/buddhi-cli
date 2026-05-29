import argparse
from buddhi_ai.commands.init_cmd import handle_init


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

    args = parser.parse_args()

    if args.command == "init":
        handle_init(args)


if __name__ == "__main__":
    main()
