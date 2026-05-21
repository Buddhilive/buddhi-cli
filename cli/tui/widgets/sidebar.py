"""Sidebar widget — lists conversations loaded from SQLite."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, ListItem, ListView, Static

from cli.tui.storage import Conversation


class ConversationItem(ListItem):
    """A single row in the conversation list."""

    def __init__(self, conv: Conversation) -> None:
        super().__init__()
        self.conv = conv

    def compose(self) -> ComposeResult:
        title = self.conv.title[:22] + "…" if len(self.conv.title) > 22 else self.conv.title
        yield Static(title, markup=False)


class Sidebar(Widget):
    """
    Left sidebar showing:
    - App branding header
    - "New Chat" button
    - Scrollable list of past conversations
    Keyboard:  n → new chat, d → delete selected, Enter → open
    """

    BINDINGS = [
        Binding("n", "new_chat", "New Chat", show=False),
        Binding("d", "delete_conv", "Delete", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static("  Buddhi AI", id="sidebar-title")
        yield Button("+ New Chat", id="new-chat-btn")
        yield ListView(id="conv-list")

    def on_mount(self) -> None:
        # List is populated by the parent screen via load_conversations()
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_conversations(self, conversations: list[Conversation]) -> None:
        """Replaces the ListView contents with the given conversation list."""
        lv: ListView = self.query_one("#conv-list", ListView)
        lv.clear()
        for conv in conversations:
            lv.append(ConversationItem(conv))

    def get_selected_conversation(self) -> Conversation | None:
        lv: ListView = self.query_one("#conv-list", ListView)
        item = lv.highlighted_child
        if isinstance(item, ConversationItem):
            return item.conv
        return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_new_chat(self) -> None:
        self.post_message(self.NewChatRequested())

    def action_delete_conv(self) -> None:
        conv = self.get_selected_conversation()
        if conv:
            self.post_message(self.DeleteRequested(conv))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-chat-btn":
            self.action_new_chat()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ConversationItem):
            self.post_message(self.ConversationSelected(event.item.conv))

    # ------------------------------------------------------------------
    # Custom messages
    # ------------------------------------------------------------------

    class NewChatRequested(Message):
        """User requested a new conversation."""

    class ConversationSelected(Message):
        """User selected an existing conversation."""
        def __init__(self, conv: Conversation) -> None:
            super().__init__()
            self.conv = conv

    class DeleteRequested(Message):
        """User requested deletion of a conversation."""
        def __init__(self, conv: Conversation) -> None:
            super().__init__()
            self.conv = conv
