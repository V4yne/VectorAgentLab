"""Storage interfaces for conversation persistence."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from vector_agent_lab.core.message import MessageRole
from vector_agent_lab.storage.models import Conversation, StoredMessage, StoredTraceEvent


class ConversationStore(ABC):
    """Abstract persistence interface for chat topics and their context."""

    @abstractmethod
    def create_conversation(
        self,
        conversation_id: str,
        title: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Conversation:
        """Create and return a conversation topic."""

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Return one conversation topic, or None if it does not exist."""

    @abstractmethod
    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """Return recent conversation topics."""

    @abstractmethod
    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredMessage:
        """Persist one chat message."""

    @abstractmethod
    def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        """Return messages in chronological order."""

    @abstractmethod
    def replace_trace(self, conversation_id: str, trace_events: list[dict[str, Any]]) -> list[StoredTraceEvent]:
        """Replace the latest visible trace for a conversation."""

    @abstractmethod
    def list_trace(self, conversation_id: str) -> list[StoredTraceEvent]:
        """Return the latest visible trace for a conversation."""

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its stored context."""
