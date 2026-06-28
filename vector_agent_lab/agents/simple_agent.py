"""SimpleAgent.

Planned responsibility:
- send user input to an LLM once
- return the model response without tool use, planning, or memory
- serve as the first teaching implementation
"""

# my_simple_agent.py
from typing import Optional, Iterator
import re
from ..core import agent, config, message, llm
from ..core.llm import VectorAgentsLLM
from ..core.config import Config
from ..core.message import Message
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
        print(f"Initialized SimpleAgent with name: {self.name}, \
                provider: {self.llm.provider}, \
                tool calling enabled: {self.enable_tool_calling}\
                config is {config}"
                )
        
    def run(self,
            input_text: str, 
            max_tool_iterations: int = 3,
            **kwargs
            ) -> str:
        """
        运行Agent,发送用户输入到LLM并返回响应
        """
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
            response = self.llm.think(formatted_messages)
            # 添加到历史记录
            self._add_message(Message(role="user", content=input_text))
            self._add_message(Message(role="assistant", content=response))
            return response
        else:
            self._run_with_tools(messages, input_text, max_tool_iterations=max_tool_iterations, **kwargs)
        # return response
    
    def _run_with_tools(self, 
                        messages: list[Message],
                        input_text: str,
                        max_tool_iterations: int = 3, 
                        **kwargs
                        ) -> str:
        current_iteration = 0
        final_reponse = ""
        while current_iteration < max_tool_iterations:
            formatted_messages = [msg.to_dict() for msg in messages]
            response = self.llm.think(formatted_messages)
            # 检查是否有工具调用
            tool_calls = self._parse_tool_calls(response)
            if tool_calls:
                print(f"监测到{len(tool_calls)}次工具调用")
                # 执行工具调用并且收集结果
                tool_results = []
                clean_response = response
                for tool_call in tool_calls:
                    result = self._execute_tool_call(tool_call['tool_name'], tool_call['parameters'])
                    tool_results.append(result)
                    clean_response = clean_response.replace(tool_call['original'], "")
                # 构建包含工具结果的消息
                messages.append(Message(role="assistant", content=clean_response))
                # 添加工具结果
                tool_results_text = "\n\n".join(tool_results)
                messages.append(Message(role="user", content=f"工具执行结果:\n{tool_results_text}\n\n请基于这些结果继续回答。"))
                
                current_iteration += 1
                continue
            #没有工具调用的时候，直接得到最终回答
            final_response = response
            break
        # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= max_tool_iterations and not final_response:
            formatted_messages = [msg.to_dict() for msg in messages]
            final_response = self.llm.think(formatted_messages, **kwargs)

        # 保存到历史记录
        self._add_message(Message(role="user", content=input_text))
        self._add_message(Message(role="assistant", content=final_response))
        print(f"✅ {self.name} 响应完成")

        return final_response

    def _parse_tool_calls(self, text: str) -> list:
        """解析文本中的工具调用"""
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
            # 智能参数解析
            if tool_name == 'calculator':
                # 计算器工具直接传入表达式
                result = self.tool_registry.execute_tool(tool_name, parameters)
            else:
                # 其他工具使用智能参数解析
                param_dict = self._parse_tool_parameters(tool_name, parameters)
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    return f"❌ 错误:未找到工具 '{tool_name}'"
                result = tool.run(param_dict)

            return f"🔧 工具 {tool_name} 执行结果:\n{result}"

        except Exception as e:
            return f"❌ 工具调用失败:{str(e)}"

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

        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt

        # 获取工具描述
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt

        tools_section = "\n\n## 可用工具\n"
        tools_section += "你可以使用以下工具来帮助回答问题:\n"
        tools_section += tools_description + "\n"

        tools_section += "\n## 工具调用格式\n"
        tools_section += "当需要使用工具时，请使用以下格式:\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += "例如:`[TOOL_CALL:search:Python编程]` 或 `[TOOL_CALL:memory:recall=用户信息]`\n\n"
        tools_section += "工具调用结果会自动插入到对话中，然后你可以基于结果继续回答。\n"

        return base_prompt + tools_section

    def _add_message(self, message: Message):
        """添加消息到历史记录"""
        self._history.append(message)

    def _format_messages(self, messages: list[Message]) -> list[dict]:
        return [msg.to_dict() for msg in messages]


if __name__ == "__main__":
    # 示例使用
    llm_client = llm.GeneralLLM()
    agent_config = config.Config.from_env()
    simple_agent = SimpleAgent(name="SimpleAgent", llm=llm_client, config=agent_config)
    while True:
        user_input = input("请输入您的问题 (或输入 'exit' 退出): ")
        if user_input.lower() == 'exit':
            break
        response = simple_agent.run(user_input)
        print(f"Agent响应: {response}")