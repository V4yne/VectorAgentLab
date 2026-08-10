"""Tool base class.

Planned responsibility:
- define the common interface for executable tools
- describe tool name, description, input schema, and output result
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time

from .schema import ToolParameter
from .response import ToolResponse

class Tool(ABC):
    """VectorAgentLab工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具"""
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass

    def run_with_timing(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行工具并包装为标准 ToolResponse。"""
        start_time = time.time()
        try:
            result = self.run(parameters)
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ToolResponse.success(
                text=str(result),
                data={"output": result},
                stats={"time_ms": elapsed_ms},
                context={"tool_name": self.name, "parameters": parameters},
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return ToolResponse.error(
                code="EXECUTION_ERROR",
                message=f"执行工具 '{self.name}' 时发生异常: {str(e)}",
                stats={"time_ms": elapsed_ms},
                context={"tool_name": self.name, "parameters": parameters},
            )
