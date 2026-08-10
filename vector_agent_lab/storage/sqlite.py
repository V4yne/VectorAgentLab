"""SQLite-backed conversation storage."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Optional, cast
from uuid import uuid4

from vector_agent_lab.core.message import MessageRole
from vector_agent_lab.storage.base import ConversationStore
from vector_agent_lab.storage.models import Conversation, StoredMessage, StoredTraceEvent


DEFAULT_DB_PATH = ".vector_agent_lab/conversations.sqlite3"


class SQLiteConversationStore(ConversationStore):
    """Persist chat topics, messages, and visible traces in SQLite."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._init_db()

    @classmethod
    def from_env(cls) -> "SQLiteConversationStore":
        """Create a store using VECTOR_AGENT_LAB_CONVERSATION_DB if present."""
        return cls(os.getenv("VECTOR_AGENT_LAB_CONVERSATION_DB", DEFAULT_DB_PATH))

    def create_conversation(
        self,
        conversation_id: str,
        title: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Conversation:
        now = _now()
        clean_title = title.strip() or "Untitled"

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    clean_title,
                    now.isoformat(),
                    now.isoformat(),
                    _dump_json(metadata or {}),
                ),
            )

        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise RuntimeError(f"Failed to create conversation: {conversation_id}")
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    c.metadata,
                    COALESCE(mc.message_count, 0) AS message_count,
                    COALESCE(
                        (
                            SELECT content
                            FROM messages
                            WHERE conversation_id = c.id
                            ORDER BY created_at DESC, id DESC
                            LIMIT 1
                        ),
                        ''
                    ) AS last_message
                FROM conversations c
                LEFT JOIN (
                    SELECT conversation_id, COUNT(*) AS message_count
                    FROM messages
                    GROUP BY conversation_id
                ) mc ON mc.conversation_id = c.id
                WHERE c.id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return _conversation_from_row(row) if row else None

    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    c.metadata,
                    COALESCE(mc.message_count, 0) AS message_count,
                    COALESCE(
                        (
                            SELECT content
                            FROM messages
                            WHERE conversation_id = c.id
                            ORDER BY created_at DESC, id DESC
                            LIMIT 1
                        ),
                        ''
                    ) AS last_message
                FROM conversations c
                LEFT JOIN (
                    SELECT conversation_id, COUNT(*) AS message_count
                    FROM messages
                    GROUP BY conversation_id
                ) mc ON mc.conversation_id = c.id
                ORDER BY c.updated_at DESC, c.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [_conversation_from_row(row) for row in rows]

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredMessage:
        message_id = uuid4().hex
        now = _now()
        metadata_json = _dump_json(metadata or {})

        with self._lock, self._connect() as conn:
            if self._conversation_missing(conn, conversation_id):
                raise ValueError(f"Conversation does not exist: {conversation_id}")

            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    now.isoformat(),
                    metadata_json,
                ),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now.isoformat(), conversation_id),
            )

        return StoredMessage(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
            metadata=metadata or {},
        )

    def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, created_at, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [_message_from_row(row) for row in rows]

    def replace_trace(self, conversation_id: str, trace_events: list[dict[str, Any]]) -> list[StoredTraceEvent]:
        now = _now()
        stored_events: list[StoredTraceEvent] = []

        with self._lock, self._connect() as conn:
            if self._conversation_missing(conn, conversation_id):
                raise ValueError(f"Conversation does not exist: {conversation_id}")

            conn.execute("DELETE FROM trace_events WHERE conversation_id = ?", (conversation_id,))
            for event in trace_events:
                event_id = uuid4().hex
                step = int(event.get("step", len(stored_events) + 1))
                event_type = str(event.get("type", "event"))
                title = str(event.get("title", event_type))
                detail = str(event.get("detail", ""))
                metadata = event.get("metadata", {})
                metadata = metadata if isinstance(metadata, dict) else {"value": metadata}

                conn.execute(
                    """
                    INSERT INTO trace_events (
                        id, conversation_id, step, type, title, detail, created_at, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        conversation_id,
                        step,
                        event_type,
                        title,
                        detail,
                        now.isoformat(),
                        _dump_json(metadata),
                    ),
                )
                stored_events.append(
                    StoredTraceEvent(
                        id=event_id,
                        conversation_id=conversation_id,
                        step=step,
                        type=event_type,
                        title=title,
                        detail=detail,
                        created_at=now,
                        metadata=metadata,
                    )
                )

        return stored_events

    def list_trace(self, conversation_id: str) -> list[StoredTraceEvent]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, step, type, title, detail, created_at, metadata
                FROM trace_events
                WHERE conversation_id = ?
                ORDER BY step ASC, created_at ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [_trace_from_row(row) for row in rows]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0

    def _init_db(self):
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS trace_events (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
                    ON messages(conversation_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_trace_conversation_step
                    ON trace_events(conversation_id, step);

                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _conversation_missing(self, conn: sqlite3.Connection, conversation_id: str) -> bool:
        row = conn.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return row is None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {"value": decoded}


def _conversation_from_row(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
        message_count=int(row["message_count"]),
        last_message=row["last_message"] or "",
        metadata=_load_json(row["metadata"]),
    )


def _message_from_row(row: sqlite3.Row) -> StoredMessage:
    return StoredMessage(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=cast(MessageRole, row["role"]),
        content=row["content"],
        created_at=_parse_datetime(row["created_at"]),
        metadata=_load_json(row["metadata"]),
    )


def _trace_from_row(row: sqlite3.Row) -> StoredTraceEvent:
    return StoredTraceEvent(
        id=row["id"],
        conversation_id=row["conversation_id"],
        step=int(row["step"]),
        type=row["type"],
        title=row["title"],
        detail=row["detail"],
        created_at=_parse_datetime(row["created_at"]),
        metadata=_load_json(row["metadata"]),
    )
