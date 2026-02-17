"""Async SQLite data-access layer for model management.

Provides CRUD operations for downloaded_models and active_downloads tables
using aiosqlite for non-blocking database access.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# ──────────────────────── SQL Statements ────────────────────────

_CREATE_DOWNLOADED_MODELS = """
CREATE TABLE IF NOT EXISTS downloaded_models (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         TEXT    NOT NULL,
    filename        TEXT    NOT NULL,
    file_path       TEXT    NOT NULL,
    file_size       INTEGER NOT NULL,
    download_date   TEXT    NOT NULL,
    repo_author     TEXT,
    repo_name       TEXT,
    quantization    TEXT,
    UNIQUE(repo_id, filename)
);
"""

_CREATE_ACTIVE_DOWNLOADS = """
CREATE TABLE IF NOT EXISTS active_downloads (
    id                TEXT    PRIMARY KEY,
    repo_id           TEXT    NOT NULL,
    filename          TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'pending',
    progress          REAL    NOT NULL DEFAULT 0.0,
    downloaded_bytes  INTEGER NOT NULL DEFAULT 0,
    total_bytes       INTEGER NOT NULL DEFAULT 0,
    error_message     TEXT,
    started_at        TEXT    NOT NULL,
    completed_at      TEXT,
    UNIQUE(repo_id, filename)
);
"""


class ModelRepository:
    """Async repository for SQLite operations on model data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(_CREATE_DOWNLOADED_MODELS)
            await db.execute(_CREATE_ACTIVE_DOWNLOADS)
            await db.commit()
        logger.info("Database initialized at %s", self.db_path)

    # ──────────────── Downloaded models CRUD ────────────────────

    async def add_downloaded_model(
        self,
        repo_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        repo_author: str | None = None,
        repo_name: str | None = None,
        quantization: str | None = None,
    ) -> int:
        """Insert a new downloaded model record. Returns the row id."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO downloaded_models
                    (repo_id, filename, file_path, file_size, download_date,
                     repo_author, repo_name, quantization)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_id,
                    filename,
                    file_path,
                    file_size,
                    datetime.now(timezone.utc).isoformat(),
                    repo_author,
                    repo_name,
                    quantization,
                ),
            )
            await db.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    async def get_all_downloaded_models(self) -> list[dict[str, Any]]:
        """Fetch all downloaded model records."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM downloaded_models ORDER BY download_date DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_downloaded_model(self, model_id: int) -> dict[str, Any] | None:
        """Fetch a single downloaded model by id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM downloaded_models WHERE id = ?", (model_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def find_downloaded_model(self, repo_id: str, filename: str) -> dict[str, Any] | None:
        """Look up a downloaded model by repo_id + filename."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM downloaded_models WHERE repo_id = ? AND filename = ?",
                (repo_id, filename),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete_downloaded_model(self, model_id: int) -> bool:
        """Delete a downloaded model record. Returns True if a row was deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM downloaded_models WHERE id = ?", (model_id,))
            await db.commit()
            return cursor.rowcount > 0

    # ──────────────── Active downloads CRUD ─────────────────────

    async def insert_active_download(
        self,
        download_id: str,
        repo_id: str,
        filename: str,
    ) -> None:
        """Create a new active download record with status 'pending'."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO active_downloads
                    (id, repo_id, filename, status, progress,
                     downloaded_bytes, total_bytes, started_at)
                VALUES (?, ?, ?, 'pending', 0.0, 0, 0, ?)
                """,
                (download_id, repo_id, filename, datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()

    async def update_download_status(
        self,
        download_id: str,
        *,
        status: str,
        progress: float = 0.0,
        downloaded_bytes: int = 0,
        total_bytes: int = 0,
        error_message: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        """Update an active download's status and progress fields."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE active_downloads
                SET status = ?, progress = ?, downloaded_bytes = ?,
                    total_bytes = ?, error_message = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, progress, downloaded_bytes, total_bytes, error_message, completed_at, download_id),
            )
            await db.commit()

    async def get_active_download(self, download_id: str) -> dict[str, Any] | None:
        """Fetch a single active download by id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM active_downloads WHERE id = ?", (download_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def find_active_download(self, repo_id: str, filename: str) -> dict[str, Any] | None:
        """Find an active download by repo_id + filename that is pending or downloading."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM active_downloads
                WHERE repo_id = ? AND filename = ? AND status IN ('pending', 'downloading')
                """,
                (repo_id, filename),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_active_downloads(self) -> list[dict[str, Any]]:
        """Fetch all active download records."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM active_downloads ORDER BY started_at DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_active_download(self, download_id: str) -> None:
        """Remove a completed/failed/cancelled download record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM active_downloads WHERE id = ?", (download_id,))
            await db.commit()
