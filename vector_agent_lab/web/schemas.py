"""API schemas for the local web app."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Browser chat request."""

    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    max_tool_iterations: int = Field(default=5, ge=1, le=10)


class TraceEvent(BaseModel):
    """One visible Agent execution event.

    This is an execution trace, not hidden model chain-of-thought.
    """

    step: int
    type: str
    title: str
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    """One saved conversation topic shown in the sidebar."""

    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    last_message: str = ""


class ConversationMessage(BaseModel):
    """One persisted chat message."""

    role: str
    content: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Browser chat response."""

    reply: str
    session_id: str
    conversation: ConversationSummary
    tools: list[str]
    trace: list[TraceEvent] = Field(default_factory=list)


class ConversationsResponse(BaseModel):
    """Saved conversation topics."""

    conversations: list[ConversationSummary]


class ConversationDetailResponse(BaseModel):
    """Saved messages and latest trace for one conversation."""

    conversation: ConversationSummary
    messages: list[ConversationMessage]
    trace: list[TraceEvent] = Field(default_factory=list)


class ToolsResponse(BaseModel):
    """Current tool catalog."""

    tools: list[str]
    description: str


class ResetResponse(BaseModel):
    """Session reset response."""

    session_id: str
    reset: bool


class DeleteConversationResponse(BaseModel):
    """Conversation deletion response."""

    session_id: str
    deleted: bool
