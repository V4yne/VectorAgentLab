"""Tool base class.

Planned responsibility:
- define the common interface for executable tools
- describe tool name, description, input schema, and output result
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

from .schema import ToolParameter

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