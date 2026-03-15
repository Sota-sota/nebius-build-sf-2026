import asyncio
from tavily import TavilyClient
from config import TAVILY_API_KEY


class TavilySearchTool:
    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY)
        self.cache: dict = {}

    async def search(self, query: str) -> list[dict]:
        if query in self.cache:
            return self.cache[query]
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.search, query, search_depth="basic", max_results=3
                ),
                timeout=5.0,
            )
            formatted = [
                {"title": r["title"], "content": r["content"][:200], "url": r["url"]}
                for r in results.get("results", [])
            ]
            self.cache[query] = formatted
            return formatted
        except Exception as e:
            print(f"[Tavily] search failed: {e}")
            return []

    async def search_for_command(self, objects: list[str], task: str, broadcast_fn) -> str:
        obj = objects[0] if objects else "object"
        queries = [
            f"{obj} weight material properties",
            f"robotic arm safe grip {obj}",
            f"robot arm {task} best practice",
        ]
        context_parts = []
        for q in queries[:3]:
            results = await self.search(q)
            await broadcast_fn({
                "type": "tavily_result",
                "data": {"query": q, "results": results},
            })
            for r in results:
                context_parts.append(f"[{r['title']}] {r['content']}")
        return "\n".join(context_parts) or "No web search results. Proceed with caution."
