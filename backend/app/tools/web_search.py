"""网络搜索工具 — 通过 DuckDuckGo 进行实时网页搜索

返回前 5 条结果的标题、摘要和链接。
依赖 ddgs 库（DuckDuckGo Search）。
"""

from app.tools.base import tool_registry


@tool_registry.register(
    name="web_search",
    description="Search the web for real-time information",
    parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]},
    risk="low",
)
async def web_search(query: str) -> str:
    """使用 DuckDuckGo 搜索网页，返回前 5 条结果"""
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return f"No results found for '{query}'"
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "")[:300]    # 截断摘要到 300 字符
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"