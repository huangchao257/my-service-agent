"""网络搜索工具 — 通过 DuckDuckGo 进行实时网页搜索

默认返回前 5 条结果（可通过 max_results 调整，上限 10）。
按 href 去重，避免同一链接重复出现。
依赖 ddgs 库（DuckDuckGo Search）。
"""

from app.tools.base import tool_registry


@tool_registry.register(
    name="web_search",
    description="Search the web for real-time information",
    parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "max_results": {"type": "integer", "description": "Max results to return (1-10, default 5)"}}, "required": ["query"]},
    risk="low",
    category="web",
)
async def web_search(query: str, max_results: int = 5) -> str:
    """使用 DuckDuckGo 搜索网页，按 href 去重，返回前 max_results 条。

    max_results 被夹到 [1, 10] 区间；超出按边界处理。"""
    # 夹到合理区间，防止模型传入异常值
    max_results = max(1, min(int(max_results), 10))
    try:
        from ddgs import DDGS
        # 多取一些以便去重后仍有足够结果
        raw = list(DDGS().text(query, max_results=max_results * 2))
        if not raw:
            return f"No results found for '{query}'"

        seen: set[str] = set()
        lines = []
        count = 0
        for r in raw:
            href = r.get("href", "")
            if href in seen:
                continue
            seen.add(href)
            title = r.get("title", "No title")
            body = (r.get("body", "") or "")[:300]  # 摘要截断到 300 字符
            lines.append(f"{count + 1}. {title}\n   {body}\n   {href}")
            count += 1
            if count >= max_results:
                break
        return "\n\n".join(lines) if lines else f"No results found for '{query}'"
    except Exception as e:
        return f"Search error: {e}"
