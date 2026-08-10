"""Tests for conversation persistence."""

from vector_agent_lab.storage import SQLiteConversationStore


def test_sqlite_conversation_store_persists_context(tmp_path):
    db_path = tmp_path / "conversations.sqlite3"
    store = SQLiteConversationStore(str(db_path))

    store.create_conversation("topic-1", "天气和时间")
    store.add_message("topic-1", "user", "现在几点？")
    store.add_message("topic-1", "assistant", "现在是北京时间。")
    store.replace_trace(
        "topic-1",
        [
            {
                "step": 1,
                "type": "tool_call",
                "title": "调用时间工具",
                "detail": "Asia/Shanghai",
                "metadata": {"tool_name": "current_time"},
            }
        ],
    )

    reloaded = SQLiteConversationStore(str(db_path))
    conversations = reloaded.list_conversations()
    messages = reloaded.list_messages("topic-1")
    trace = reloaded.list_trace("topic-1")

    assert conversations[0].id == "topic-1"
    assert conversations[0].title == "天气和时间"
    assert conversations[0].message_count == 2
    assert conversations[0].last_message == "现在是北京时间。"
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "现在几点？"
    assert trace[0].type == "tool_call"
    assert trace[0].metadata["tool_name"] == "current_time"
