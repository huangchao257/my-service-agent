"""
工具模块 — 导出工具注册中心和所有内置工具

内置工具：
- system_tools: get_current_time（时间查询）、calculator（数学计算）
- web_search: 通过 DuckDuckGo 搜索网页
- file_ops: read_file / write_file（安全文件读写）
- code_executor: 子进程 Python 代码执行
"""

from app.tools.base import tool_registry, ToolDefinition
from app.tools import system_tools, web_search, file_ops, code_executor, dev_tools

__all__ = ["tool_registry", "ToolDefinition"]