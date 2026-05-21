"""ChatMessage widget — renders user and assistant messages."""
from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.widgets import Markdown, Static
from textual.widget import Widget


def _relative_time(iso: str) -> str:
    """Converts an ISO timestamp to a human-readable relative string."""
    try:
        then = datetime.fromisoformat(iso)
        now = datetime.now(timezone.utc)
        diff = int((now - then).total_seconds())
        if diff < 60:
            return "just now"
        elif diff < 3600:
            return f"{diff // 60}m ago"
        elif diff < 86400:
            return f"{diff // 3600}h ago"
        else:
            return then.strftime("%b %d")
    except Exception:
        return ""


class ChatMessage(Widget):
    """
    A single chat message bubble.
    - role="user"      → terracotta left border, right-indented
    - role="assistant" → warm border, Markdown rendered content
    """

    DEFAULT_CSS = ""

    def __init__(
        self,
        role: str,
        content: str,
        created_at: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.role = role
        self.content = content
        self.created_at = created_at

    def compose(self) -> ComposeResult:
        role_label = "You" if self.role == "user" else "Buddhi"
        time_str = _relative_time(self.created_at) if self.created_at else ""

        if self.role == "user":
            yield Static(
                f"[bold]{role_label}[/bold]  [dim]{time_str}[/dim]",
                classes="message-role",
            )
            yield Static(self.content, classes="message-content-user")
        else:
            yield Static(
                f"[bold]{role_label}[/bold]  [dim]{time_str}[/dim]",
                classes="message-role-assistant",
            )
            yield Markdown(self.content, classes="message-content-assistant")

    def get_css_classes(self) -> list[str]:
        base = super().get_css_classes()
        if self.role == "user":
            base.append("message-user")
        else:
            base.append("message-assistant")
        return base

    def append_delta(self, delta: str) -> None:
        """
        Appends streaming delta text to an assistant message.
        Called repeatedly as tokens arrive.
        """
        self.content += delta
        # Refresh the Markdown widget with the updated content
        try:
            md = self.query_one(Markdown)
            md.update(self.content)
        except Exception:
            pass
