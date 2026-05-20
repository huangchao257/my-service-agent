"""
工具注册中心 — 内置工具的定义、注册和查询。

每个工具有 risk 等级（low/medium/high），高风险工具执行前需要用户确认。
通过 @tool_registry.register() 装饰器注册新工具，自动生成 OpenAI function calling 格式的 schema。
"""

from typing import Callable
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """工具定义数据类"""
    name: str            # 工具名称（LLM function calling 使用）
    description: str     # 工具描述（供 LLM 理解用途）
    parameters: dict     # JSON Schema 格式的参数定义
    function: Callable   # 实际执行函数
    risk: str = "low"    # 风险等级：low / medium / high


class ToolRegistry:
    """工具注册中心，管理所有已注册的工具"""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, parameters: dict, risk: str = "low"):
        """装饰器：注册一个新工具"""
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name, description=description, parameters=parameters, function=func, risk=risk,
            )
            return func
        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        """按名称获取工具定义"""
        return self._tools.get(name)

    def get_schemas(self, names: list[str]) -> list[dict]:
        """将指定工具列表转换为 OpenAI function calling 格式的 schema 列表"""
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
        """列出所有已注册的工具"""
        return list(self._tools.values())

    def requires_confirmation(self, name: str) -> bool:
        """检查工具是否需要用户确认（风险等级为 high）"""
        tool = self._tools.get(name)
        return tool.risk == "high" if tool else False


# 全局工具注册中心实例
tool_registry = ToolRegistry()