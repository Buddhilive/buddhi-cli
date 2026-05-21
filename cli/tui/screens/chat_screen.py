"""ChatScreen — the main full-screen chat view."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, VerticalScroll
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Static

from cli.tui.client import BuddhiClient
from cli.tui.storage import Conversation, Message, store
from cli.tui.widgets.input_bar import InputBar
from cli.tui.widgets.message import ChatMessage


class ChatScreen(Screen):
    """
    The main chat interface:
    - Scrollable message history (top, 1fr)
    - InputBar at the bottom (auto-height)
    - Streams assistant replies token-by-token
    - Persists all messages to SQLite
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", show=False),
    ]

    def __init__(
        self,
        conversation: Conversation,
        messages: list[Message],
        client: BuddhiClient,
    ) -> None:
        super().__init__()
        self._conv = conversation
        self._history: list[Message] = list(messages)
        self._client = client
        self._streaming = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="message-list"):
            for msg in self._history:
                yield ChatMessage(
                    role=msg.role,
                    content=msg.content,
                    created_at=msg.created_at,
                )
            yield LoadingIndicator(id="loading")
        yield InputBar(id="input-bar")

    def on_mount(self) -> None:
        self.query_one("#loading").display = False
        self._scroll_to_bottom()

    # ------------------------------------------------------------------
    # Message submission
    # ------------------------------------------------------------------

    async def on_input_bar_submitted(self, event: InputBar.Submitted) -> None:
        """Handles user submit → appends bubble, streams response."""
        text = event.text.strip()
        if not text or self._streaming:
            return

        # 1. Show user bubble immediately
        now = datetime.now(timezone.utc).isoformat()
        user_msg = await store.append_message(self._conv.id, "user", text)
        self._history.append(user_msg)

        user_bubble = ChatMessage(role="user", content=text, created_at=now)
        await self._append_widget(user_bubble)

        # Auto-title conversation from first message
        if len(self._history) == 1:
            await store.auto_title_from_first_message(self._conv.id, text)

        # 2. Lock input while streaming
        self._streaming = True
        self.query_one(InputBar).set_streaming(True)
        self.query_one("#loading").display = True
        self._scroll_to_bottom()

        # 3. Create assistant bubble (empty, fills via deltas)
        ai_bubble = ChatMessage(
            role="assistant",
            content="",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await self._append_widget(ai_bubble)

        # 4. Stream
        full_response = ""
        try:
            messages_payload = [
                {"role": m.role, "content": m.content}
                for m in self._history
            ]
            async for delta in self._client.stream_chat(messages_payload):
                full_response += delta
                ai_bubble.append_delta(delta)
                self._scroll_to_bottom()
        except ConnectionError as exc:
            ai_bubble.append_delta(f"\n\n[error] {exc}")
        except Exception as exc:
            ai_bubble.append_delta(f"\n\n[error] Unexpected error: {exc}")
        finally:
            # 5. Persist assistant reply
            if full_response:
                ai_msg = await store.append_message(
                    self._conv.id, "assistant", full_response
                )
                self._history.append(ai_msg)

            # 6. Unlock input
            self.query_one("#loading").display = False
            self._streaming = False
            self.query_one(InputBar).set_streaming(False)
            self._scroll_to_bottom()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _append_widget(self, widget: ChatMessage) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        loading = self.query_one("#loading")
        await container.mount(widget, before=loading)

    def _scroll_to_bottom(self) -> None:
        container = self.query_one("#message-list", ScrollableContainer)
        container.scroll_end(animate=False)
