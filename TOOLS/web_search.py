"""
Web Search Tool
Allows JARVIS to search the internet autonomously.
"""
from duckduckgo_search import DDGS

class WebSearch:
    @staticmethod
    def search(query: str, max_results=3) -> str:
        print(f"[WEB SEARCH] Searching DuckDuckGo for: '{query}'")
        try:
            results = DDGS().text(query, max_results=max_results)
            if not results:
                return "No results found."
                
            formatted = ""
            for i, r in enumerate(results):
                formatted += f"{i+1}. {r['title']}\n"
                formatted += f"   Snippet: {r['body']}\n"
                formatted += f"   URL: {r['href']}\n\n"
                
            print("[WEB SEARCH] Successfully retrieved search results.")
            return formatted.strip()
        except Exception as e:
            print(f"[WEB SEARCH ERROR] {e}")
            return f"Search failed: {e}"
