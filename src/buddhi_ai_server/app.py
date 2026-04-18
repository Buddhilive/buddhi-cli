from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label
from textual.containers import Center, Middle


class BuddhiAIApp(App):
    """A Textual app to display Hello World for Buddhi AI Server."""

    TITLE = "Buddhi AI Server"

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit the app"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        with Center():
            with Middle():
                yield Label(
                    "Hello World! Welcome to Buddhi AI Server.", id="hello-label"
                )

        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


def run():
    """Run the application."""
    app = BuddhiAIApp()
    app.run()


if __name__ == "__main__":
    run()
