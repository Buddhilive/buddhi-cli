"""
BuddhiApp — root Textual application.

Layout:
  ┌────────────┬──────────────────────────────┐
  │  Sidebar   │       ChatScreen / Welcome   │
  │  (28 cols) │           (1fr)              │
  └────────────┴──────────────────────────────┘
  │          Status Bar (1 row)               │
  └───────────────────────────────────────────┘

Startup sequence:
  1. Check if FastAPI backend is reachable.
  2. If not → auto-start in background thread (spinner shown).
  3. Initialize SQLite store.
  4. Load conversation list into sidebar.
  5. Show WelcomeScreen or resume last conversation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Footer, Label, Static

from cli.tui.client import BuddhiClient
from cli.tui.screens.chat_screen import ChatScreen
from cli.tui.screens.welcome_screen import WelcomeScreen
from cli.tui.server_manager import ensure_server_ready
from cli.tui.storage import Conversation, store
from cli.tui.widgets.sidebar import Sidebar

CSS_PATH = Path(__file__).parent / "styles" / "theme.tcss"

# ---------------------------------------------------------------------------
# Help modal
# ---------------------------------------------------------------------------

HELP_CONTENT = """[bold $primary]Buddhi AI — Keyboard Shortcuts[/bold $primary]

[bold]Navigation[/bold]
  [bold]n[/bold]          New conversation
  [bold]j / k[/bold]      Move up/down in sidebar
  [bold]Tab[/bold]        Switch focus (sidebar ↔ chat)
  [bold]Enter[/bold]      Open selected conversation
  [bold]d[/bold]          Delete selected conversation

[bold]Chat[/bold]
  [bold]Enter[/bold]      Send message
  [bold]Shift+Enter[/bold] Insert newline
  [bold]Esc[/bold]        Back to welcome screen

[bold]App[/bold]
  [bold]?[/bold]          Toggle this help
  [bold]q[/bold]          Quit
"""


class HelpOverlay(ModalScreen):
    """Full-screen dimmed help overlay — dismiss with any key."""

    BINDINGS = [
        Binding("escape,q,question_mark,space", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static(HELP_CONTENT, id="help-panel")

    def on_key(self, _: object) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Status Bar
# ---------------------------------------------------------------------------

class StatusBar(Static):
    """One-row status line docked at the bottom."""

    def __init__(self) -> None:
        super().__init__(id="status-bar")
        self._server_ok = False

    def compose(self) -> ComposeResult:
        yield Label("  Buddhi AI", id="status-model")
        yield Label("  ●  server: checking…", id="status-server")

    def set_server_status(self, ok: bool) -> None:
        self._server_ok = ok
        try:
            lbl = self.query_one("#status-server", Label)
            if ok:
                lbl.update("  ●  server: ready")
                lbl.remove_class("offline")
            else:
                lbl.update("  ●  server: offline")
                lbl.add_class("offline")
        except NoMatches:
            pass


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class BuddhiApp(App):
    """Root Textual application for Buddhi AI TUI."""

    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("n", "new_chat", "New Chat", show=True),
        Binding("question_mark", "toggle_help", "Help", show=True),
        Binding("tab", "cycle_focus", "Focus", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._client = BuddhiClient()
        self._current_conv: Optional[Conversation] = None

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-area"):
            yield Sidebar(id="sidebar")
            yield WelcomeScreen()
        yield StatusBar()
        yield Footer()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def on_mount(self) -> None:
        """
        1. Ensure server is running (auto-start if needed).
        2. Init SQLite store.
        3. Load conversations into sidebar.
        """
        # Update status immediately
        status_bar = self.query_one(StatusBar)

        # Run server-start in a worker so the TUI renders first
        self.run_worker(self._startup_sequence(), exclusive=True)

    async def _startup_sequence(self) -> None:
        status_bar = self.query_one(StatusBar)

        # 1. Ensure server ready (blocking poll in thread pool)
        import asyncio
        server_ok = await asyncio.to_thread(
            ensure_server_ready,
            on_starting=lambda: self.call_from_thread(
                lambda: status_bar.query_one(
                    "#status-server", Label
                ).update("  ◌  server: starting…")
            )
        )
        status_bar.set_server_status(server_ok)

        # 2. Init SQLite
        await store.initialize()

        # 3. Load conversations
        await self._refresh_sidebar()

    async def _refresh_sidebar(self) -> None:
        conversations = await store.get_conversations()
        sidebar = self.query_one(Sidebar)
        sidebar.load_conversations(conversations)

    # ------------------------------------------------------------------
    # Sidebar event handlers
    # ------------------------------------------------------------------

    async def on_sidebar_new_chat_requested(
        self, _: Sidebar.NewChatRequested
    ) -> None:
        await self.action_new_chat()

    async def on_sidebar_conversation_selected(
        self, event: Sidebar.ConversationSelected
    ) -> None:
        await self._open_conversation(event.conv)

    async def on_sidebar_delete_requested(
        self, event: Sidebar.DeleteRequested
    ) -> None:
        await store.delete_conversation(event.conv.id)
        if (
            self._current_conv
            and self._current_conv.id == event.conv.id
        ):
            self._current_conv = None
            await self._show_welcome()
        await self._refresh_sidebar()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def action_new_chat(self) -> None:
        conv = await store.create_conversation("New Chat")
        await self._refresh_sidebar()
        await self._open_conversation(conv)

    async def action_toggle_help(self) -> None:
        await self.push_screen(HelpOverlay())

    def action_cycle_focus(self) -> None:
        self.screen.focus_next()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _open_conversation(self, conv: Conversation) -> None:
        self._current_conv = conv
        messages = await store.get_messages(conv.id)
        # Replace the content area (right of sidebar) with a ChatScreen widget
        try:
            old = self.query_one("#main-area").children[-1]
            await old.remove()
        except Exception:
            pass
        chat = ChatScreen(conv, messages, self._client)
        chat.id = "active-chat"
        await self.query_one("#main-area").mount(chat)

    async def _show_welcome(self) -> None:
        try:
            old = self.query_one("#active-chat")
            await old.remove()
        except NoMatches:
            pass
        await self.query_one("#main-area").mount(WelcomeScreen())

    async def action_show_welcome(self) -> None:
        """Called by ChatScreen's Escape binding."""
        self._current_conv = None
        await self._show_welcome()
