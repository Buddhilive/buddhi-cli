from textual.app import ComposeResult
from textual.widgets import Static, Input, Markdown
from textual.containers import VerticalScroll, Vertical

class ChatArea(Static):
    DEFAULT_CSS = """
    ChatArea {
        width: 1fr;
        background: $background;
    }
    #chat-history {
        height: 1fr;
        padding: 2 4;
    }
    #chat-input-container {
        height: auto;
        dock: bottom;
        padding: 1 4 2 4;
    }
    #chat-input {
        width: 1fr;
        border: vkey $surface-lighten-1;
        background: $surface;
    }
    #chat-input:focus {
        border: vkey $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="chat-history"):
            yield Markdown(
                "### Mock Chat History\n\n"
                "**User**: Hello!\n\n"
                "**Buddhi**: Hi there! How can I help you today?\n\n"
                "**User**: Who is the best footballer of all time?\n\n"
                "**Buddhi**: That is a highly debated topic. Some say Messi, others say Ronaldo. Both are exceptional players."
            )
        
        with Vertical(id="chat-input-container"):
            yield Input(placeholder="Send a message to the model...", id="chat-input")
