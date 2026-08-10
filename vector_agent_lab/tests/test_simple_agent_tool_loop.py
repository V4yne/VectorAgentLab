"""Tests for SimpleAgent tool-loop behavior."""

from vector_agent_lab.agents.simple_agent import SimpleAgent
from vector_agent_lab.tools.registry import ToolRegistry


class FakeLLM:
    provider = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.messages_seen = []

    def think(self, messages, **kwargs):
        self.messages_seen.append(messages)
        return self.responses.pop(0)


def test_simple_agent_repairs_incomplete_tool_intent():
    llm = FakeLLM(
        [
            "让我尝试获取一个天气网站的具体信息。",
            "[TOOL_CALL:fake_search:上海徐汇区天气]",
            "最终答案：上海徐汇区天气查询完成。",
        ]
    )

    registry = ToolRegistry()
    registry.register_function(
        name="fake_search",
        description="测试搜索工具",
        func=lambda query: f"搜索结果: {query}",
    )

    agent = SimpleAgent(
        name="TestAgent",
        llm=llm,
        tool_registry=registry,
    )

    response = agent.run("上海徐汇区天气如何？")

    assert response == "最终答案：上海徐汇区天气查询完成。"
    assert len(llm.messages_seen) == 3
    repair_messages = llm.messages_seen[1]
    assert any(
        "你刚才表示还要继续查询或获取信息" in message["content"]
        for message in repair_messages
    )


def test_simple_agent_forces_search_for_fresh_public_health_question():
    llm = FakeLLM(
        [
            "建议查看中国疾控中心等官方渠道。",
            "最终答案：已基于最新搜索结果总结全国流行病毒情况。",
        ]
    )

    registry = ToolRegistry()
    registry.register_function(
        name="advanced_search",
        description="测试实时搜索工具",
        func=lambda query: f"搜索结果: {query}",
    )

    agent = SimpleAgent(
        name="TestAgent",
        llm=llm,
        tool_registry=registry,
    )

    response = agent.run("最近全国有什么比较流行的疫情或者病毒吗？")
    trace = agent.get_last_trace()

    assert response == "最终答案：已基于最新搜索结果总结全国流行病毒情况。"
    assert len(llm.messages_seen) == 2
    assert any(
        "我已经自动调用搜索工具" in message["content"]
        and "搜索结果: 最近全国有什么比较流行的疫情或者病毒吗？ 官方 最新 全国 疾控 监测 通报" in message["content"]
        for message in llm.messages_seen[1]
    )
    assert any(
        event["type"] == "tool_policy"
        and event["metadata"]["tool_name"] == "advanced_search"
        for event in trace
    )
