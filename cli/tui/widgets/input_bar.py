"""InputBar widget — multi-line text input with send button."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, TextArea


class InputBar(Widget):
    """
    Bottom input area:
    - TextArea for multi-line input
    - Send button
    - Enter → submit, Shift+Enter → newline
    - Disables itself while the AI is streaming
    """

    BINDINGS = [
        Binding("ctrl+s", "submit", "Send", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield TextArea(
            id="chat-input",
            language=None,
            soft_wrap=True,
            show_line_numbers=False,
        )
        yield Button("  Send", id="send-btn", variant="default")

    def on_mount(self) -> None:
        self.query_one(TextArea).focus()
        self._update_placeholder()

    def _update_placeholder(self) -> None:
        # TextArea doesn't have native placeholder; set initial text hint
        ta = self.query_one(TextArea)
        if not ta.text:
            ta.load_text("")

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def on_key(self, event: "events.Key") -> None:  # type: ignore[name-defined]
        if event.key == "enter":
            # Only intercept plain Enter (not Shift+Enter which TextArea handles)
            event.stop()
            self.action_submit()

    def action_submit(self) -> None:
        ta = self.query_one(TextArea)
        text = ta.text.strip()
        if not text:
            return
        ta.load_text("")
        # Post a custom message up to the parent screen
        self.post_message(self.Submitted(text))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            self.action_submit()

    # ------------------------------------------------------------------
    # Streaming lock helpers
    # ------------------------------------------------------------------

    def set_streaming(self, streaming: bool) -> None:
        """Disables input while streaming, re-enables when done."""
        ta = self.query_one(TextArea)
        btn = self.query_one(Button)
        ta.disabled = streaming
        btn.disabled = streaming
        if streaming:
            btn.add_class("streaming")
        else:
            btn.remove_class("streaming")
            ta.focus()

    # ------------------------------------------------------------------
    # Custom message
    # ------------------------------------------------------------------

    class Submitted(Message):
        """Posted when the user submits a message."""
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text
