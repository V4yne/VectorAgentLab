"""Time tool.

Provides a lightweight function tool for getting the current time.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from ..registry import ToolRegistry


def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """Return the current time for a given timezone."""
    timezone = (timezone or "Asia/Shanghai").strip() or "Asia/Shanghai"

    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        return f"❌ 无效时区: {timezone}"

    return now.strftime(f"当前时间是 %Y-%m-%d %H:%M:%S，时区: {timezone}")


def register_time_tool(registry: ToolRegistry) -> ToolRegistry:
    """Register the current_time function tool into an existing registry."""
    registry.register_function(
        name="current_time",
        description="获取当前时间。参数是时区，例如 Asia/Shanghai、UTC、America/New_York。",
        func=get_current_time,
    )
    return registry


def create_time_registry() -> ToolRegistry:
    """Create a registry containing only the current_time tool."""
    registry = ToolRegistry()
    return register_time_tool(registry)

