"""
SQLite-backed conversation persistence.

Database location: ~/.buddhi/data/chat.db
Schema:
  conversations(id TEXT PK, title TEXT, created_at TEXT)
  messages(id TEXT PK, conversation_id TEXT FK, role TEXT,
           content TEXT, created_at TEXT)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

# ---------------------------------------------------------------------------
# DB path
# ---------------------------------------------------------------------------

DB_DIR = Path.home() / ".buddhi" / "data"
DB_PATH = DB_DIR / "chat.db"

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Conversation:
    id: str
    title: str
    created_at: str


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str          # "user" | "assistant"
    content: str
    created_at: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# ChatStore
# ---------------------------------------------------------------------------


class ChatStore:
    """Async CRUD interface backed by aiosqlite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    async def initialize(self) -> None:
        """Create the DB directory and tables if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id         TEXT PRIMARY KEY,
                    title      TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id              TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id)
                                         ON DELETE CASCADE,
                    role            TEXT NOT NULL,
                    content         TEXT NOT NULL,
                    created_at      TEXT NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conv "
                "ON messages(conversation_id)"
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    async def create_conversation(
        self, title: str = "New Chat"
    ) -> Conversation:
        conv = Conversation(id=_new_id(), title=title, created_at=_now_iso())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO conversations VALUES (?, ?, ?)",
                (conv.id, conv.title, conv.created_at),
            )
            await db.commit()
        return conv

    async def get_conversations(self) -> list[Conversation]:
        """Returns all conversations newest-first."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM conversations ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
        return [Conversation(**dict(r)) for r in rows]

    async def rename_conversation(self, conv_id: str, new_title: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (new_title, conv_id),
            )
            await db.commit()

    async def delete_conversation(self, conv_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM conversations WHERE id = ?", (conv_id,)
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    async def append_message(
        self, conversation_id: str, role: str, content: str
    ) -> Message:
        msg = Message(
            id=_new_id(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=_now_iso(),
        )
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?)",
                (msg.id, msg.conversation_id, msg.role, msg.content, msg.created_at),
            )
            await db.commit()
        return msg

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """Returns messages for a conversation, oldest-first."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at ASC",
                (conversation_id,),
            )
            rows = await cursor.fetchall()
        return [Message(**dict(r)) for r in rows]

    async def auto_title_from_first_message(
        self, conv_id: str, user_content: str
    ) -> None:
        """
        Generates a short title (first 50 chars of first user message)
        and updates the conversation.
        """
        title = user_content.strip().split("\n")[0][:50]
        if not title:
            title = "New Chat"
        await self.rename_conversation(conv_id, title)


# Singleton for the TUI to import
store = ChatStore()
