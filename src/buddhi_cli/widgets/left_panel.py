from textual.app import ComposeResult
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Vertical

class LeftPanel(Static):
    DEFAULT_CSS = """
    LeftPanel {
        width: 30;
        dock: left;
        background: $surface;
        border-right: vkey $background;
    }
    .panel-title {
        padding: 1 2;
        text-style: bold;
        color: $text-muted;
        width: 100%;
    }
    #chat-list {
        height: 1fr;
        padding: 0 1;
    }
    ListItem {
        padding: 1;
        margin-bottom: 1;
        background: transparent;
    }
    ListItem:hover {
        background: $surface-lighten-1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Chats", classes="panel-title")
        with Vertical(id="chat-list"):
            yield ListView(
                ListItem(Label("General Chat")),
                ListItem(Label("Python Help")),
                ListItem(Label("Project Planning")),
                ListItem(Label("Debugging TUI")),
            )
