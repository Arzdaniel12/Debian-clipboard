"""Local SQLite storage for clipboard entries."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ClipboardItem:
    id: int
    kind: str
    text: str | None
    data: bytes
    created_at: str


class ClipboardStore:
    """Store clipboard data locally, newest first, with deterministic deduplication."""

    def __init__(self, path: str | Path, limit: int = 100) -> None:
        if limit < 1:
            raise ValueError("limit must be positive")
        self.path = Path(path).expanduser()
        self.limit = limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS clipboard_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('text', 'image')),
                text TEXT,
                data BLOB NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        self.connection.commit()
        self._trim()

    def close(self) -> None:
        self.connection.close()

    def add_text(self, text: str) -> bool:
        if not text:
            return False
        return self._add("text", text, text.encode("utf-8"))

    def add_image(self, png_data: bytes) -> bool:
        if not png_data:
            return False
        return self._add("image", None, png_data)

    def _add(self, kind: str, text: str | None, data: bytes) -> bool:
        fingerprint = hashlib.sha256(kind.encode() + b"\0" + data).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO clipboard_items(kind, text, data, fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
            (kind, text, data, fingerprint, timestamp),
        )
        self.connection.commit()
        if cursor.rowcount:
            self._trim()
            return True
        return False

    def _trim(self) -> None:
        self.connection.execute(
            "DELETE FROM clipboard_items WHERE id NOT IN (SELECT id FROM clipboard_items ORDER BY id DESC LIMIT ?)",
            (self.limit,),
        )
        self.connection.commit()

    def items(self, search: str = "") -> list[ClipboardItem]:
        if search:
            pattern = f"%{search}%"
            rows = self.connection.execute(
                "SELECT id, kind, text, data, created_at FROM clipboard_items "
                "WHERE text LIKE ? OR (kind = 'image' AND ? = 'image') ORDER BY id DESC",
                (pattern, search.lower()),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT id, kind, text, data, created_at FROM clipboard_items ORDER BY id DESC"
            ).fetchall()
        return [ClipboardItem(row["id"], row["kind"], row["text"], bytes(row["data"]), row["created_at"]) for row in rows]

    def delete(self, item_id: int) -> None:
        self.connection.execute("DELETE FROM clipboard_items WHERE id = ?", (item_id,))
        self.connection.commit()

    def clear(self) -> None:
        self.connection.execute("DELETE FROM clipboard_items")
        self.connection.commit()

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM clipboard_items").fetchone()[0])