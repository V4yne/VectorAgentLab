"""Factory helpers for the local VectorAgentLab web app."""

from threading import Lock
from typing import Optional
from uuid import uuid4

from vector_agent_lab.agents.simple_agent import SimpleAgent
from vector_agent_lab.core import config, llm
from vector_agent_lab.core.message import Message
from vector_agent_lab.storage import Conversation, ConversationStore, SQLiteConversationStore, StoredMessage, StoredTraceEvent
from vector_agent_lab.tools.builtin.search import create_advanced_search_registry
from vector_agent_lab.tools.builtin.time import register_time_tool
from vector_agent_lab.tools.registry import ToolRegistry


def build_tool_registry() -> ToolRegistry:
    """Create the local tools used by the web test bench."""
    registry = create_advanced_search_registry()
    register_time_tool(registry)
    return registry


def create_simple_agent(
    tool_registry: Optional[ToolRegistry] = None,
    history: Optional[list[Message]] = None,
) -> SimpleAgent:
    """Create a SimpleAgent wired to the current .env LLM config and local tools."""
    llm_client = llm.GeneralLLM()
    agent_config = config.Config.from_env()
    agent = SimpleAgent(
        name="WebSimpleAgent",
        llm=llm_client,
        config=agent_config,
        tool_registry=tool_registry or build_tool_registry(),
    )
    if history:
        agent.load_history(history)
    return agent


class AgentSessionManager:
    """Small in-memory session manager for browser chat sessions."""

    def __init__(self, store: Optional[ConversationStore] = None):
        self._sessions: dict[str, SimpleAgent] = {}
        self._lock = Lock()
        self._tool_registry = build_tool_registry()
        self._store = store or SQLiteConversationStore.from_env()

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        max_tool_iterations: int = 5,
    ) -> tuple[str, str, list[dict], Conversation]:
        """Run one chat turn and return the session id, reply, trace, and topic."""
        session_id = session_id or uuid4().hex

        with self._lock:
            if self._store.get_conversation(session_id) is None:
                self._store.create_conversation(session_id, _make_title(message))

            agent = self._sessions.get(session_id)
            if agent is None:
                history = self._load_history(session_id)
                agent = create_simple_agent(tool_registry=self._tool_registry, history=history)
                self._sessions[session_id] = agent

            reply = agent.run(message, max_tool_iterations=max_tool_iterations)
            trace = agent.get_last_trace()
            self._store.add_message(session_id, "user", message)
            self._store.add_message(session_id, "assistant", reply or "")
            self._store.replace_trace(session_id, trace)
            conversation = self._store.get_conversation(session_id)

        if conversation is None:
            raise RuntimeError(f"Conversation disappeared during chat: {session_id}")
        return session_id, reply, trace, conversation

    def reset(self, session_id: str) -> bool:
        """Drop one in-memory Agent session while keeping persisted history."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def delete(self, session_id: str) -> bool:
        """Delete one persisted conversation and any in-memory Agent."""
        with self._lock:
            self._sessions.pop(session_id, None)
            return self._store.delete_conversation(session_id)

    def list_conversations(self) -> list[Conversation]:
        """Return saved conversation topics."""
        return self._store.list_conversations()

    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """Return one saved conversation topic."""
        return self._store.get_conversation(session_id)

    def list_messages(self, session_id: str) -> list[StoredMessage]:
        """Return stored messages for one conversation."""
        return self._store.list_messages(session_id)

    def list_trace(self, session_id: str) -> list[StoredTraceEvent]:
        """Return stored trace events for one conversation."""
        return self._store.list_trace(session_id)

    def list_tools(self) -> list[str]:
        """Return registered tool names."""
        return self._tool_registry.list_tools()

    def get_tools_description(self) -> str:
        """Return the human-readable tool catalog."""
        return self._tool_registry.get_tools_description()

    def _load_history(self, session_id: str) -> list[Message]:
        return [
            Message(
                role=message.role,
                content=message.content,
                timestamp=message.created_at,
                metadata=message.metadata,
            )
            for message in self._store.list_messages(session_id)
        ]


def _make_title(text: str, max_chars: int = 32) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return "Untitled"
    return clean[:max_chars] + ("..." if len(clean) > max_chars else "")
