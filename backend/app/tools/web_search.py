import httpx
from app.tools.base import tool_registry


@tool_registry.register(
    name="web_search",
    description="Search the web using DuckDuckGo",
    parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]},
    risk="low",
)
async def web_search(query: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1},
                timeout=10,
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return f"Search result: {abstract}"
            related = data.get("RelatedTopics", [])
            if related:
                results = [item.get("Text", "") for item in related[:3] if item.get("Text")]
                return "Search results:\n" + "\n".join(f"- {r}" for r in results)
            return f"No results found for '{query}'"
    except Exception as e:
        return f"Search error: {e}"