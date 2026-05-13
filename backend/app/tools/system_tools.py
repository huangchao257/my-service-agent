from datetime import datetime
from app.tools.base import tool_registry


@tool_registry.register(
    name="get_current_time",
    description="Get the current date and time",
    parameters={"type": "object", "properties": {"timezone": {"type": "string", "description": "Timezone, e.g. Asia/Shanghai. Defaults to UTC."}}},
    risk="low",
)
async def get_current_time(timezone: str = "UTC") -> str:
    return f"Current time: {datetime.utcnow().isoformat()} UTC"


@tool_registry.register(
    name="calculator",
    description="Evaluate a mathematical expression",
    parameters={"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression, e.g. '2 + 3 * 4'"}}, "required": ["expression"]},
    risk="low",
)
async def calculator(expression: str) -> str:
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return "Error: expression contains disallowed characters"
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"