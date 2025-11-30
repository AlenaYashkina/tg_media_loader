"""SQLite-backed ledger for downloaded media."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class DownloadDB:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS downloaded_media (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                media_index INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                date_iso TEXT,
                downloaded_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_downloaded_media
            ON downloaded_media(chat_id, message_id, media_index)
            WHERE status = 'success'
            """
        )
        self._conn.commit()

    def already_downloaded(self, chat_id: int, message_id: int, media_index: int) -> bool:
        cursor = self._conn.execute(
            """
            SELECT 1 FROM downloaded_media
            WHERE chat_id = ? AND message_id = ? AND media_index = ? AND status = 'success'
            """,
            (chat_id, message_id, media_index),
        )
        return cursor.fetchone() is not None

    def get_record(
        self, chat_id: int, message_id: int, media_index: int
    ) -> Optional[sqlite3.Row]:
        cursor = self._conn.execute(
            """
            SELECT file_path, file_size, mime_type, status FROM downloaded_media
            WHERE chat_id = ? AND message_id = ? AND media_index = ?
            ORDER BY id DESC LIMIT 1
            """,
            (chat_id, message_id, media_index),
        )
        return cursor.fetchone()

    def record_media(
        self,
        *,
        chat_id: int,
        message_id: int,
        media_index: int,
        media_type: str,
        file_path: str,
        file_size: Optional[int],
        mime_type: Optional[str],
        date_iso: str,
        status: str,
    ) -> None:
        downloaded_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO downloaded_media (
                chat_id, message_id, media_index, media_type,
                file_path, file_size, mime_type, date_iso, downloaded_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                message_id,
                media_index,
                media_type,
                file_path,
                file_size,
                mime_type,
                date_iso,
                downloaded_at,
                status,
            ),
        )
        self._conn.commit()
