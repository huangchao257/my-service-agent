from typing import Callable
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    function: Callable
    risk: str = "low"


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, parameters: dict, risk: str = "low"):
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name, description=description, parameters=parameters, function=func, risk=risk,
            )
            return func
        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_schemas(self, names: list[str]) -> list[dict]:
        schemas = []
        for name in names:
            tool = self._tools.get(name)
            if tool:
                schemas.append({
                    "type": "function",
                    "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
                })
        return schemas

    def list_all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def requires_confirmation(self, name: str) -> bool:
        tool = self._tools.get(name)
        return tool.risk == "high" if tool else False


tool_registry = ToolRegistry()