"""Data models for persisted conversations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vector_agent_lab.core.message import MessageRole


@dataclass(frozen=True)
class Conversation:
    """A saved conversation topic."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StoredMessage:
    """One message persisted inside a conversation."""

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StoredTraceEvent:
    """One visible execution trace event persisted for a conversation."""

    id: str
    conversation_id: str
    step: int
    type: str
    title: str
    detail: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
