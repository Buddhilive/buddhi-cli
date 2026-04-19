from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual_pyfiglet import FigletWidget
import importlib.metadata


# Get app version from pyproject.toml
def _get_version() -> str:
    try:
        return importlib.metadata.version("buddhi-ai-server")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


class BuddhiAIApp(App):
    """A Textual app to display Hello World for Buddhi AI Server."""

    TITLE = "Buddhi AI Server"
    SUB_TITLE = f"Version {_get_version()}"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit the app"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)

        yield FigletWidget(
            "Buddhi AI Server",
            font="ansi_shadow",
            justify="center",
            colors=["#e6a08f", "#e05d38"],
            animate=True,
            classes="buddhi-ai-server-title",
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
