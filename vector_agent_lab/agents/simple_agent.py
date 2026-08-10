"""SimpleAgent.

Planned responsibility:
- send user input to an LLM once
- return the model response without tool use, planning, or memory
- serve as the first teaching implementation
"""

# my_simple_agent.py
from typing import Any, Optional
import re
from ..core import config, llm
from ..core.llm import VectorAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..tools.builtin.search import create_advanced_search_registry
from ..tools.builtin.time import register_time_tool
# from ..agents import Agent

class SimpleAgent():
    """
    重写的简单对话Agent
    展示如何基于框架基类构建自定义Agent
    """

    def __init__(
        self,
        name: str,
        llm: VectorAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self._history: list[Message] = []
        self._last_trace: list[dict[str, Any]] = []
        print(f"Initialized SimpleAgent with name: {self.name}, \
                provider: {self.llm.provider}, \
                tool calling enabled: {self.enable_tool_calling}\
                config is {config}"
                )
        
    def run(self,
            input_text: str, 
            max_tool_iterations: int = 5,
            **kwargs
            ) -> str:
        """
        运行Agent,发送用户输入到LLM并返回响应
        """
        self._reset_trace()
        self._add_trace_event(
            event_type="agent_start",
            title="开始运行 Agent",
            detail=input_text,
            metadata={
                "agent_name": self.name,
                "provider": getattr(self.llm, "provider", "unknown"),
                "model": getattr(self.llm, "model_name", None),
                "tool_calling": self.enable_tool_calling,
            },
        )

        # 构建消息列表
        messages = []

        # 1. 添加系统提示词
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append(Message(role="system", content=enhanced_system_prompt))
        # 2. 添加历史消息
        for msg in self._history:
            messages.append(msg)
        # 3. 加入本次对话
        messages.append(Message(role="user", content=input_text))

        # 调用LLM
        # 如果没有启动工具调用，直接简单响应
        if not self.enable_tool_calling:
            formatted_messages = [msg.to_dict() for msg in messages]
            self._add_trace_event(
                event_type="llm_request",
                title="发送 LLM 请求",
                detail=f"message_count={len(formatted_messages)}",
                metadata={"message_count": len(formatted_messages)},
            )
            response = self.llm.think(formatted_messages)
            self._add_trace_event(
                event_type="llm_response",
                title="收到 LLM 响应",
                detail=response or "",
            )
            # 添加到历史记录
            self._add_message(Message(role="user", content=input_text))
            self._add_message(Message(role="assistant", content=response))
            self._add_trace_event(
                event_type="final_answer",
                title="生成最终回答",
                detail=response or "",
            )
            return response
        else:
            return self._run_with_tools(messages, input_text, max_tool_iterations=max_tool_iterations, **kwargs)
        # return response
    
    def _run_with_tools(self, 
                        messages: list[Message],
                        input_text: str,
                        max_tool_iterations: int = 5,
                        **kwargs
                        ) -> str:
        current_iteration = 0
        final_response = ""
        executed_tool_names: list[str] = []
        while current_iteration < max_tool_iterations:
            formatted_messages = [msg.to_dict() for msg in messages]
            self._add_trace_event(
                event_type="llm_request",
                title="发送 LLM 请求",
                detail=f"iteration={current_iteration + 1}, message_count={len(formatted_messages)}",
                metadata={
                    "iteration": current_iteration + 1,
                    "message_count": len(formatted_messages),
                },
            )
            response = self.llm.think(formatted_messages)
            self._add_trace_event(
                event_type="llm_response",
                title="收到 LLM 响应",
                detail=response or "",
                metadata={"iteration": current_iteration + 1},
            )
            # 检查是否有工具调用
            tool_calls = self._parse_tool_calls(response)
            if tool_calls:
                print(f"监测到{len(tool_calls)}次工具调用")
                self._add_trace_event(
                    event_type="tool_calls_detected",
                    title="检测到工具调用",
                    detail=f"共 {len(tool_calls)} 次工具调用",
                    metadata={"count": len(tool_calls), "iteration": current_iteration + 1},
                )
                # 执行工具调用并且收集结果
                tool_results = []
                clean_response = response
                for tool_call in tool_calls:
                    self._add_trace_event(
                        event_type="tool_call",
                        title=f"调用工具 {tool_call['tool_name']}",
                        detail=tool_call["parameters"],
                        metadata={
                            "tool_name": tool_call["tool_name"],
                            "parameters": tool_call["parameters"],
                            "iteration": current_iteration + 1,
                        },
                    )
                    result = self._execute_tool_call(tool_call['tool_name'], tool_call['parameters'])
                    executed_tool_names.append(tool_call["tool_name"])
                    tool_results.append(result)
                    self._add_trace_event(
                        event_type="tool_result",
                        title=f"工具 {tool_call['tool_name']} 返回结果",
                        detail=result,
                        metadata={
                            "tool_name": tool_call["tool_name"],
                            "iteration": current_iteration + 1,
                        },
                    )
                    print(self._format_tool_result_preview(result))
                    clean_response = clean_response.replace(tool_call['original'], "")
                # 构建包含工具结果的消息
                messages.append(Message(role="assistant", content=clean_response))
                # 添加工具结果
                tool_results_text = "\n\n".join(tool_results)
                messages.append(Message(role="user", content=f"工具执行结果:\n{tool_results_text}\n\n请基于这些结果继续回答。"))
                
                current_iteration += 1
                continue

            if self._requires_fresh_search(input_text, executed_tool_names):
                search_query = self._build_fresh_search_query(input_text)
                print("⚠️ 当前问题需要实时搜索，已自动调用 advanced_search。")
                self._add_trace_event(
                    event_type="tool_policy",
                    title="实时信息问题触发强制搜索",
                    detail=search_query,
                    metadata={
                        "tool_name": "advanced_search",
                        "iteration": current_iteration + 1,
                    },
                )
                self._add_trace_event(
                    event_type="tool_call",
                    title="调用工具 advanced_search",
                    detail=search_query,
                    metadata={
                        "tool_name": "advanced_search",
                        "parameters": search_query,
                        "iteration": current_iteration + 1,
                        "forced": True,
                    },
                )
                result = self._execute_tool_call("advanced_search", search_query)
                executed_tool_names.append("advanced_search")
                self._add_trace_event(
                    event_type="tool_result",
                    title="工具 advanced_search 返回结果",
                    detail=result,
                    metadata={
                        "tool_name": "advanced_search",
                        "iteration": current_iteration + 1,
                        "forced": True,
                    },
                )
                print(self._format_tool_result_preview(result))
                messages.append(Message(role="assistant", content=response or ""))
                messages.append(
                    Message(
                        role="user",
                        content=(
                            "这个问题涉及最新或实时信息，不能只基于模型记忆回答。"
                            "我已经自动调用搜索工具，结果如下:\n"
                            f"{result}\n\n"
                            "请优先基于工具结果回答。"
                            "如果问题涉及公共卫生、疫情、病毒或医疗风险，请区分官方来源和非官方来源，"
                            "说明信息时间，并避免给出超出搜索结果支持的确定性结论。"
                        ),
                    )
                )
                current_iteration += 1
                continue

            if self._looks_like_incomplete_tool_intent(response):
                print("⚠️ 检测到模型想继续查询但没有按格式调用工具，已追加纠偏提示。")
                self._add_trace_event(
                    event_type="repair",
                    title="追加工具调用纠偏提示",
                    detail=response or "",
                    metadata={"iteration": current_iteration + 1},
                )
                messages.append(Message(role="assistant", content=response))
                messages.append(
                    Message(
                        role="user",
                        content=(
                            "你刚才表示还要继续查询或获取信息，但没有输出工具调用。"
                            "如果还需要查询，请立即只输出一个或多个工具调用，格式必须是 "
                            "`[TOOL_CALL:{tool_name}:{parameters}]`。"
                            "如果已有信息足够，请不要再说“让我尝试/继续查询”，直接给最终答案。"
                        ),
                    )
                )
                current_iteration += 1
                continue

            #没有工具调用的时候，直接得到最终回答
            final_response = response
            self._add_trace_event(
                event_type="final_answer",
                title="生成最终回答",
                detail=final_response or "",
                metadata={"iteration": current_iteration + 1},
            )
            break
        # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= max_tool_iterations and not final_response:
            formatted_messages = [msg.to_dict() for msg in messages]
            self._add_trace_event(
                event_type="llm_request",
                title="超过工具轮数后请求最终回答",
                detail=f"message_count={len(formatted_messages)}",
                metadata={"message_count": len(formatted_messages), "max_tool_iterations": max_tool_iterations},
            )
            final_response = self.llm.think(formatted_messages, **kwargs)
            self._add_trace_event(
                event_type="final_answer",
                title="生成最终回答",
                detail=final_response or "",
                metadata={"max_tool_iterations": max_tool_iterations},
            )

        # 保存到历史记录
        self._add_message(Message(role="user", content=input_text))
        self._add_message(Message(role="assistant", content=final_response))
        print(f"✅ {self.name} 响应完成")

        return final_response

    def get_last_trace(self) -> list[dict[str, Any]]:
        """返回最近一次 run 的执行轨迹。"""
        return [event.copy() for event in self._last_trace]

    def get_history(self) -> list[Message]:
        """返回当前对话历史。"""
        return self._history.copy()

    def load_history(self, messages: list[Message]):
        """加载历史消息，用于从持久化会话恢复上下文。"""
        self._history = messages.copy()

    def clear_history(self):
        """清空当前对话历史。"""
        self._history.clear()

    def _reset_trace(self):
        """清空上一轮执行轨迹。"""
        self._last_trace = []

    def _add_trace_event(
        self,
        event_type: str,
        title: str,
        detail: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ):
        """记录一条可展示的执行轨迹事件。"""
        self._last_trace.append(
            {
                "step": len(self._last_trace) + 1,
                "type": event_type,
                "title": title,
                "detail": self._truncate_trace_detail(detail),
                "metadata": metadata or {},
            }
        )

    def _truncate_trace_detail(self, detail: Any, max_chars: int = 4000) -> str:
        """限制 Trace 明细长度，避免搜索结果把页面撑爆。"""
        text = "" if detail is None else str(detail)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...<trace detail truncated>"

    def _parse_tool_calls(self, text: str) -> list:
        """解析文本中的工具调用"""
        if not text:
            return []

        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
        matches = re.findall(pattern, text)

        tool_calls = []
        for tool_name, parameters in matches:
            tool_calls.append({
                'tool_name': tool_name.strip(),
                'parameters': parameters.strip(),
                'original': f'[TOOL_CALL:{tool_name}:{parameters}]'
            })

        return tool_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行工具调用"""
        if not self.tool_registry:
            return f"❌ 错误:未配置工具注册表"

        try:
            result = self.tool_registry.execute_tool(tool_name, parameters)
            result_text = getattr(result, "text", str(result))
            return f"🔧 工具 {tool_name} 执行结果:\n{result_text}"

        except Exception as e:
            return f"❌ 工具调用失败:{str(e)}"

    def _format_tool_result_preview(self, result: str, max_chars: int = 1200) -> str:
        """格式化工具结果预览，避免调试输出过长。"""
        preview = result if len(result) <= max_chars else result[:max_chars] + "\n...<工具结果已截断>"
        return f"[tool debug] {preview}"

    def _looks_like_incomplete_tool_intent(self, text: str) -> bool:
        """判断回复是否像是半成品工具意图，而不是最终答案。"""
        if not text:
            return False

        normalized = text.strip()
        intent_phrases = [
            "让我尝试",
            "我来尝试",
            "让我继续",
            "我继续",
            "让我再",
            "我再查询",
            "我再搜索",
            "我再获取",
            "需要进一步查询",
            "继续查询",
            "获取一个",
            "获取一下",
            "查询一下",
            "搜索一下",
            "fetch",
            "抓取",
        ]
        return any(phrase in normalized for phrase in intent_phrases)

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict:
        """智能解析工具参数"""
        param_dict = {}

        if '=' in parameters:
            # 格式: key=value 或 action=search,query=Python
            if ',' in parameters:
                # 多个参数:action=search,query=Python,limit=3
                pairs = parameters.split(',')
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        param_dict[key.strip()] = value.strip()
            else:
                # 单个参数:key=value
                key, value = parameters.split('=', 1)
                param_dict[key.strip()] = value.strip()
        else:
            # 直接传入参数，根据工具类型智能推断
            if tool_name == 'search':
                param_dict = {'query': parameters}
            elif tool_name == 'memory':
                param_dict = {'action': 'search', 'query': parameters}
            else:
                param_dict = {'input': parameters}

        return param_dict

    def _get_enhanced_system_prompt(self) -> str:
        """构建增强的系统提示词，包含工具信息"""
        """这部分是我们的额外增强性质的系统提示词，能让本Agent在有工具的情况下更好地使用工具"""
        base_prompt = self.system_prompt or "你是一个有用的AI助手。"
        prompt_sections = [base_prompt]

        if not self.enable_tool_calling or not self.tool_registry:
            return "".join(prompt_sections)

        # 获取工具描述
        tools_description = self.tool_registry.get_tools_description()
        print(f"[tool debug] 可用工具:\n{tools_description}")
        if not tools_description or tools_description == "暂无可用工具":
            return "".join(prompt_sections)

        tools_section = "\n\n## 可用工具\n"
        tools_section += "你可以使用以下工具来帮助回答问题:\n"
        tools_section += tools_description + "\n"

        tools_section += "\n## 工具调用格式\n"
        tools_section += "当需要使用工具时，请使用以下格式:\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += "请只使用上面“可用工具”列表里真实存在的工具名。\n"
        tools_section += "例如:`[TOOL_CALL:advanced_search:Python编程最新趋势]`\n"
        tools_section += "例如:`[TOOL_CALL:current_time:Asia/Shanghai]`\n\n"
        tools_section += "当用户问题涉及今天、最近、最新、当前、实时、本周、本月、今年等动态信息时，不要凭模型记忆直接回答，必须先调用合适工具。\n"
        tools_section += "当用户问题涉及新闻、天气、政策、价格、疫情、病毒、公共卫生、病例、比赛等可能变化的信息时，优先调用 `advanced_search`。\n"
        tools_section += "公共卫生和医疗相关实时问题要优先搜索官方或权威来源，并说明信息时间与不确定性。\n"
        tools_section += "如果你说“我将查询/让我尝试/继续获取”，必须立刻输出工具调用，不要只描述计划。\n"
        tools_section += "工具调用结果会自动插入到对话中，然后你可以基于结果继续回答。\n"
        tools_section += "当工具结果已经足够回答用户问题时，请直接给最终答案，不要再输出“让我继续查询”这类半成品回复。\n"
        tools_section += "如果工具失败，请说明失败原因，并基于已有信息给出可操作建议。\n"

        prompt_sections.append(tools_section)
        return "".join(prompt_sections)

    def _add_message(self, message: Message):
        """添加消息到历史记录"""
        self._history.append(message)

    def _format_messages(self, messages: list[Message]) -> list[dict]:
        return [msg.to_dict() for msg in messages]

    def _requires_fresh_search(self, input_text: str, executed_tool_names: list[str]) -> bool:
        """判断用户问题是否必须先搜索最新信息。"""
        if not self.tool_registry or "advanced_search" not in self.tool_registry.list_tools():
            return False
        if "advanced_search" in executed_tool_names:
            return False

        normalized = input_text.strip().lower()
        freshness_terms = [
            "最近",
            "最新",
            "当前",
            "现在",
            "今天",
            "今日",
            "实时",
            "目前",
            "近期",
            "这几天",
            "本周",
            "本月",
            "今年",
            "2026",
            "latest",
            "recent",
            "current",
            "today",
            "now",
        ]
        dynamic_domains = [
            "疫情",
            "病毒",
            "传染病",
            "病例",
            "流行",
            "公共卫生",
            "疾控",
            "天气",
            "新闻",
            "政策",
            "价格",
            "汇率",
            "股价",
            "比赛",
            "发布",
            "通报",
            "数据",
            "趋势",
            "outbreak",
            "virus",
            "news",
            "weather",
        ]

        return any(term in normalized for term in freshness_terms) and any(
            term in normalized for term in dynamic_domains
        )

    def _build_fresh_search_query(self, input_text: str) -> str:
        """为实时问题构建默认搜索查询。"""
        normalized = input_text.strip()
        public_health_terms = ["疫情", "病毒", "传染病", "病例", "公共卫生", "疾控", "流行"]
        if any(term in normalized for term in public_health_terms):
            return f"{normalized} 官方 最新 全国 疾控 监测 通报"
        return f"{normalized} 最新 实时"


if __name__ == "__main__":
    # 示例使用
    llm_client = llm.GeneralLLM()
    agent_config = config.Config.from_env()
    tool_registry = create_advanced_search_registry()
    register_time_tool(tool_registry)
    print("🧩 SimpleAgent 已启用 tools backend: advanced_search + current_time")

    simple_agent = SimpleAgent(
        name="SimpleAgent",
        llm=llm_client,
        config=agent_config,
        tool_registry=tool_registry,
    )
    
    while True:
        user_input = input("请输入您的问题 (或输入 'exit' 退出): ")
        if user_input.lower() == 'exit':
            break
        response = simple_agent.run(user_input)
        print(f"Agent响应: {response}")
