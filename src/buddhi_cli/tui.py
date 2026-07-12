from textual.app import App, ComposeResult
from buddhi_cli.screens.chat_screen import ChatScreen

class BuddhiApp(App):
    CSS = """
    """
    BINDINGS = [("q", "quit", "Quit")]

    async def on_mount(self) -> None:
        await self.push_screen(ChatScreen())

if __name__ == "__main__":
    app = BuddhiApp()
    app.run()
