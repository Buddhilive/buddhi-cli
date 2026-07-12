from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import Vertical

class Sidebar(Static):
    DEFAULT_CSS = """
    Sidebar {
        width: 6;
        dock: left;
        background: $surface-darken-1;
        border-right: vkey $surface;
        align: center top;
        padding-top: 2;
    }
    .sidebar-icon {
        padding: 1;
        text-align: center;
        content-align: center middle;
        color: $text-muted;
    }
    .sidebar-icon:hover {
        color: $text;
        background: $surface-lighten-1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("💬", classes="sidebar-icon", id="icon-chat"),
            Static("🔍", classes="sidebar-icon", id="icon-search"),
            Static("⚙️", classes="sidebar-icon", id="icon-settings"),
        )
