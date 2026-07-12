import argparse
import sys
from buddhi_cli import __version__
from buddhi_cli.tui import BuddhiApp

def cli():
    parser = argparse.ArgumentParser(description="Buddhi CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show the current version")

    args = parser.parse_args()

    if args.command == "version":
        print(f"Buddhi CLI version {__version__}")
        sys.exit(0)
    
    # Default behavior: run TUI
    app = BuddhiApp()
    app.run()

if __name__ == "__main__":
    cli()
