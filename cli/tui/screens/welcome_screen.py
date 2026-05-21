"""Welcome / splash screen shown when no conversation is active."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

LOGO = """
██████╗ ██╗   ██╗██████╗ ██████╗ ██╗  ██╗██╗
██╔══██╗██║   ██║██╔══██╗██╔══██╗██║  ██║██║
██████╔╝██║   ██║██║  ██║██║  ██║███████║██║
██╔══██╗██║   ██║██║  ██║██║  ██║██╔══██║██║
██████╔╝╚██████╔╝██████╔╝██████╔╝██║  ██║██║
╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝
"""

SHORTCUTS = [
    ("n", "New conversation"),
    ("j / k", "Navigate conversations"),
    ("Enter", "Open conversation"),
    ("d", "Delete conversation"),
    ("?", "Show help"),
    ("q", "Quit"),
]


class WelcomeScreen(Screen):
    """
    Full-screen welcome shown on launch when no conversation is selected.
    Displays the Buddhi logo and a keyboard shortcut cheat-sheet.
    """

    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="welcome-logo")
        yield Static(
            "Your local AI assistant — keyboard-driven, always private.",
            id="welcome-subtitle",
        )
        yield self._shortcuts_panel()

    def _shortcuts_panel(self) -> Static:
        lines = ["[bold]Keyboard Shortcuts[/bold]\n"]
        for key, desc in SHORTCUTS:
            lines.append(
                f"  [bold $primary]{key:<12}[/bold $primary]  "
                f"[dim]{desc}[/dim]"
            )
        return Static("\n".join(lines), id="welcome-shortcuts")
