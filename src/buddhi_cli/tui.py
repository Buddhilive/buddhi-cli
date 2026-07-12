from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Center, Middle

class WelcomeScreen(Static):
    def compose(self) -> ComposeResult:
        yield Center(Middle(Static("Namo Buddhaya!", id="welcome-message")))

class BuddhiApp(App):
    CSS = """
    #welcome-message {
        content-align: center middle;
        text-style: bold;
        color: auto;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield WelcomeScreen()
        yield Footer()

if __name__ == "__main__":
    app = BuddhiApp()
    app.run()
