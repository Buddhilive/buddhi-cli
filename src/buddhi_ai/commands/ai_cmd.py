import argparse
from buddhi_ai.tui.app import BuddhiChatApp

def handle_ai(args: argparse.Namespace) -> None:
    """Launch the interactive Terminal User Interface (TUI) Chat."""
    app = BuddhiChatApp()
    app.run()
