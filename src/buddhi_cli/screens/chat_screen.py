from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.containers import Horizontal

from buddhi_cli.widgets.sidebar import Sidebar
from buddhi_cli.widgets.left_panel import LeftPanel
from buddhi_cli.widgets.chat_area import ChatArea
from buddhi_cli.widgets.right_panel import RightPanel

class ChatScreen(Screen):
    CSS = """
    #main-container {
        height: 1fr;
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            yield Sidebar()
            yield LeftPanel()
            yield ChatArea()
            yield RightPanel()
        yield Footer()
