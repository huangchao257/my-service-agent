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
    category: str = "general"  # 分类：system / web / file / code / dev 等，前端分组展示用


class ToolRegistry:
    """工具注册中心，管理所有已注册的工具"""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, parameters: dict, risk: str = "low", category: str = "general"):
        """装饰器：注册一个新工具"""
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name, description=description, parameters=parameters,
                function=func, risk=risk, category=category,
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

    def validate_args(self, name: str, args: dict) -> str | None:
        """按工具的 JSON Schema 校验参数，返回错误消息或 None（通过）。

        校验内容：
        - required 字段是否齐全
        - 已提供字段的类型是否匹配 schema（string/integer/number/boolean/array/object）
        类型不匹配时尝试做温和强转（如 "123"→123 for integer），无法强转则报错。
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Unknown tool: {name}"
        schema = tool.parameters or {}
        props = schema.get("properties", {}) or {}
        required = schema.get("required", []) or []

        # 缺失必填
        missing = [r for r in required if r not in args or args.get(r) is None]
        if missing:
            return f"Missing required parameter(s): {', '.join(missing)}"

        # 类型校验与温和强转
        type_map = {
            "string": str, "integer": int, "number": (int, float),
            "boolean": bool, "array": list, "object": dict,
        }
        for key, value in list(args.items()):
            spec = props.get(key) or {}
            expected = spec.get("type")
            if not expected or expected not in type_map:
                continue
            expected_py = type_map[expected]
            # bool 是 int 的子类，需单独处理避免被当 integer 通过
            if expected == "boolean" and not isinstance(value, bool):
                return f"Parameter '{key}' must be a boolean"
            if expected == "integer" and isinstance(value, bool):
                return f"Parameter '{key}' must be an integer, not boolean"
            if isinstance(value, expected_py) and not (expected in ("integer", "number") and isinstance(value, bool)):
                continue
            # 尝试温和强转：string→int/number
            if expected in ("integer", "number") and isinstance(value, str):
                try:
                    args[key] = int(value) if expected == "integer" else float(value)
                    continue
                except ValueError:
                    return f"Parameter '{key}' must be {expected}, got '{value}'"
            if expected == "string" and not isinstance(value, str):
                args[key] = str(value)
                continue
            # 类型不符且无法强转
            if not isinstance(value, expected_py):
                return f"Parameter '{key}' must be {expected}, got {type(value).__name__}"
        return None


# 全局工具注册中心实例
tool_registry = ToolRegistry()