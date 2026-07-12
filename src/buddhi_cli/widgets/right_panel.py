from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical

class RightPanel(Static):
    DEFAULT_CSS = """
    RightPanel {
        width: 35;
        dock: right;
        background: $surface;
        border-left: vkey $background;
    }
    .panel-title {
        padding: 1 2;
        text-style: bold;
        color: $text-muted;
        width: 100%;
    }
    .integration-item {
        padding: 1 2;
        width: 100%;
    }
    .integration-header {
        padding: 1 2;
        text-style: bold;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Integrations", classes="panel-title")
        with Vertical():
            yield Label("Available Plugins", classes="integration-header")
            yield Label("🟢 js-code-sandbox", classes="integration-item")
            yield Label("⚪ rag-v1", classes="integration-item")
