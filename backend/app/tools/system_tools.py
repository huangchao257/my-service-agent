"""系统工具 — 时间查询和数学计算"""

from datetime import datetime
from app.tools.base import tool_registry


@tool_registry.register(
    name="get_current_time",
    description="Get the current date and time",
    parameters={"type": "object", "properties": {"timezone": {"type": "string", "description": "Timezone, e.g. Asia/Shanghai. Defaults to UTC."}}},
    risk="low",
    category="system",
)
async def get_current_time(timezone: str = "UTC") -> str:
    """获取当前 UTC 时间"""
    return f"Current time: {datetime.utcnow().isoformat()} UTC"


@tool_registry.register(
    name="calculator",
    description="Evaluate a mathematical expression",
    parameters={"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression, e.g. '2 + 3 * 4'"}}, "required": ["expression"]},
    risk="low",
    category="system",
)
async def calculator(expression: str) -> str:
    """安全地计算数学表达式。
    仅允许数字和基本运算符，使用受限的 eval（禁用内置函数）防止代码注入。"""
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return "Error: expression contains disallowed characters"
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"