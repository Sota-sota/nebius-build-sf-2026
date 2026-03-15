"""
Tavily SDK wrapper with:
1. Response caching (in-memory dict, keyed by query)
2. Rate limiting (max 3 queries per command)
3. Error handling with graceful fallback
4. Result formatting for LLM consumption
5. Cache eviction every 100 entries
"""

import asyncio
from tavily import TavilyClient
from config import TAVILY_API_KEY

MAX_CACHE_SIZE = 100
SEARCH_TIMEOUT = 5.0
MAX_QUERIES_PER_COMMAND = 3


class TavilySearchTool:
    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY)
        self.cache: dict[str, list[dict]] = {}

    def _evict_cache(self):
        """Clear cache if it exceeds MAX_CACHE_SIZE."""
        if len(self.cache) >= MAX_CACHE_SIZE:
            self.cache.clear()

    async def search(self, query: str) -> list[dict]:
        """Execute a single search with caching and timeout."""
        if query in self.cache:
            return self.cache[query]

        self._evict_cache()

        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.search, query, search_depth="basic", max_results=3
                ),
                timeout=SEARCH_TIMEOUT,
            )
            formatted = [
                {
                    "title": r["title"],
                    "content": r["content"][:200],
                    "url": r["url"],
                    "score": r.get("score", 0),
                }
                for r in results.get("results", [])
            ]
            self.cache[query] = formatted
            return formatted
        except asyncio.TimeoutError:
            print(f"[Tavily] Timeout for query: {query}")
            return []
        except Exception as e:
            print(f"[Tavily] Search failed: {e}")
            return []

    async def get_context(self, query: str) -> str:
        """Use Tavily's get_search_context for RAG-style context."""
        try:
            context = await asyncio.wait_for(
                asyncio.to_thread(self.client.get_search_context, query),
                timeout=SEARCH_TIMEOUT,
            )
            return context
        except Exception as e:
            print(f"[Tavily] get_search_context failed: {e}")
            return ""

    def _generate_queries(self, objects: list[str], task: str) -> list[str]:
        """Generate targeted search queries based on objects and task."""
        queries = []
        obj = objects[0] if objects else "object"

        # Object-specific query
        queries.append(f"{obj} properties weight fragility")

        # Safety query
        queries.append(f"is {obj} safe to grip robotically")

        # Task-specific query
        task_words = task.lower().split()
        # Extract verb from command for more targeted search
        action_verbs = {"pick", "grab", "move", "sort", "hand", "place", "push", "pull", "lift", "stack"}
        verb = next((w for w in task_words if w in action_verbs), "handle")
        queries.append(f"robot arm {verb} {obj} best approach")

        return queries[:MAX_QUERIES_PER_COMMAND]

    async def search_for_command(
        self,
        objects: list[str],
        task: str,
        broadcast_fn,
    ) -> str:
        """
        Run up to 3 targeted searches for a command.
        Broadcasts each result to the frontend.
        Returns a formatted context string for the LLM.
        """
        queries = self._generate_queries(objects, task)
        context_parts = []

        for q in queries:
            results = await self.search(q)
            await broadcast_fn({
                "type": "tavily_result",
                "data": {"query": q, "results": results},
            })
            for r in results:
                context_parts.append(f"[{r['title']}] {r['content']}")

        return (
            "\n".join(context_parts)
            or "No web search results available. Proceed with caution."
        )
