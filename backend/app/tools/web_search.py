from app.tools.base import tool_registry


@tool_registry.register(
    name="web_search",
    description="Search the web for real-time information",
    parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]},
    risk="low",
)
async def web_search(query: str) -> str:
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return f"No results found for '{query}'"
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "")[:300]
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"