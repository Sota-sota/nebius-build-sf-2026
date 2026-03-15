import sys
sys.path.insert(0, "../backend")
from tavily import TavilyClient
from config import TAVILY_API_KEY

c = TavilyClient(api_key=TAVILY_API_KEY)
r = c.search("ceramic mug weight", search_depth="basic", max_results=2)
print("Tavily OK:", [x["title"] for x in r["results"]])
