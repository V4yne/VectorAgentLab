"""FastAPI entry point for the local VectorAgentLab web test bench."""

import argparse
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vector_agent_lab.web.agent_factory import AgentSessionManager
from vector_agent_lab.storage import Conversation, StoredMessage, StoredTraceEvent
from vector_agent_lab.web.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationMessage,
    ConversationSummary,
    ConversationsResponse,
    DeleteConversationResponse,
    ResetResponse,
    ToolsResponse,
    TraceEvent,
)


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="VectorAgentLab Web", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

session_manager = AgentSessionManager()


@app.get("/")
def index():
    """Serve the browser chat UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Basic health endpoint for start scripts and local checks."""
    return {"status": "ok"}


@app.get("/api/tools", response_model=ToolsResponse)
def tools() -> ToolsResponse:
    """Return the currently registered local tools."""
    return ToolsResponse(
        tools=session_manager.list_tools(),
        description=session_manager.get_tools_description(),
    )


@app.get("/api/conversations", response_model=ConversationsResponse)
def conversations() -> ConversationsResponse:
    """Return saved browser conversation topics."""
    return ConversationsResponse(
        conversations=[
            _conversation_summary(conversation)
            for conversation in session_manager.list_conversations()
        ]
    )


@app.get("/api/conversations/{session_id}", response_model=ConversationDetailResponse)
def conversation_detail(session_id: str) -> ConversationDetailResponse:
    """Return one conversation with its visible context and latest trace."""
    conversation = session_manager.get_conversation(session_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    return ConversationDetailResponse(
        conversation=_conversation_summary(conversation),
        messages=[
            _conversation_message(message)
            for message in session_manager.list_messages(session_id)
        ],
        trace=[
            _trace_event(event)
            for event in session_manager.list_trace(session_id)
        ],
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run one Agent chat turn."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    try:
        session_id, reply, trace, conversation = session_manager.chat(
            message,
            session_id=request.session_id,
            max_tool_iterations=request.max_tool_iterations,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        conversation=_conversation_summary(conversation),
        tools=session_manager.list_tools(),
        trace=trace,
    )


@app.post("/api/sessions/{session_id}/reset", response_model=ResetResponse)
def reset_session(session_id: str) -> ResetResponse:
    """Reset one browser chat session."""
    return ResetResponse(session_id=session_id, reset=session_manager.reset(session_id))


@app.delete("/api/conversations/{session_id}", response_model=DeleteConversationResponse)
def delete_conversation(session_id: str) -> DeleteConversationResponse:
    """Delete one saved conversation."""
    return DeleteConversationResponse(
        session_id=session_id,
        deleted=session_manager.delete(session_id),
    )


def _conversation_summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=conversation.message_count,
        last_message=conversation.last_message,
    )


def _conversation_message(message: StoredMessage) -> ConversationMessage:
    return ConversationMessage(
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat(),
        metadata=message.metadata,
    )


def _trace_event(event: StoredTraceEvent) -> TraceEvent:
    return TraceEvent(
        step=event.step,
        type=event.type,
        title=event.title,
        detail=event.detail,
        metadata=event.metadata,
    )


def main():
    """Run the local web server."""
    parser = argparse.ArgumentParser(description="Run VectorAgentLab web test bench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
