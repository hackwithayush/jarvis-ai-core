"""
Anime Engine — Jikan API (MyAnimeList) Integration
Ensures JARVIS provides real-time, accurate anime metadata and avoids hallucinations.
"""
import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class AnimeEngine:
    """Neural Node for live anime metadata retrieval."""
    
    BASE_URL = "https://api.jikan.moe/v4"

    @classmethod
    def search_anime(cls, query: str, limit: int = 5) -> List[Dict]:
        """Search for anime series with live status and season data."""
        try:
            logger.info(f"Anime Node: Searching Jikan registry for '{query}'...")
            response = requests.get(f"{cls.BASE_URL}/anime", params={"q": query, "limit": limit}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("data", []):
                results.append({
                    "title": item.get("title"),
                    "type": item.get("type"),
                    "episodes": item.get("episodes"),
                    "status": item.get("status"),
                    "airing": item.get("airing"),
                    "season": item.get("season"),
                    "year": item.get("year"),
                    "score": item.get("score"),
                    "synopsis": item.get("synopsis", "")[:200] + "...",
                    "url": item.get("url")
                })
            return results
        except Exception as e:
            logger.error(f"Anime Node Failure: {e}")
            return []

    @classmethod
    def get_seasonal_anime(cls, status: str = "now", limit: int = 10) -> List[Dict]:
        """Fetch currently airing or upcoming anime to prevent fake season numbering."""
        try:
            endpoint = f"{cls.BASE_URL}/seasons/{status}"
            logger.info(f"Anime Node: Fetching seasonal data from {endpoint}...")
            response = requests.get(endpoint, params={"limit": limit}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("data", []):
                results.append({
                    "title": item.get("title"),
                    "type": item.get("type"),
                    "status": item.get("status"),
                    "season": item.get("season"),
                    "year": item.get("year"),
                    "score": item.get("score")
                })
            return results
        except Exception as e:
            logger.error(f"Seasonal Node Failure: {e}")
            return []

def get_anime_briefing(query: str) -> str:
    """Generates a tactical text briefing for the LLM based on live data."""
    results = AnimeEngine.search_anime(query)
    if not results:
        return "NO LIVE DATA FOUND. DO NOT HALLUCINATE."
    
    briefing = "\n--- LIVE ANIME REGISTRY DATA (TRUTH SOURCE) ---\n"
    for r in results:
        briefing += f"- {r['title']} ({r['type']})\n"
        briefing += f"  Status: {r['status']} | Episodes: {r['episodes']}\n"
        briefing += f"  Release: {r['season']} {r['year']} | Score: {r['score']}\n"
        briefing += f"  URL: {r['url']}\n\n"
    briefing += "--- END LIVE DATA ---\n"
    return briefing
