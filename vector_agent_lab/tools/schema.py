"""Tool schema definitions.

Planned responsibility:
- describe tool input parameters in a structured way
- support future conversion to JSON Schema or provider-native tool schemas
"""
from pydantic import BaseModel
from typing import Any

class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None