"""
Web Search Engine — DuckDuckGo Live Search Integration
Real-time web search with intent detection and context formatting.
No API key required.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import config
from core.utils import retry_sync

logger = logging.getLogger(__name__)

# ─── Safe Import ────────────────────────────────────────────────
WEB_SEARCH_AVAILABLE = True
try:
    from duckduckgo_search import DDGS
except ImportError:
    logger.warning("⚠️ Web search disabled: pip install duckduckgo-search")
    WEB_SEARCH_AVAILABLE = False

try:
    import trafilatura
    SCRAPER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Scraper disabled: pip install trafilatura")
    SCRAPER_AVAILABLE = False


# ─── Intent Detection Keywords ─────────────────────────────────
SEARCH_TRIGGERS = {
    "strong": [
        "search for", "search about", "look up", "google",
        "find information", "find info", "web search",
        "what is happening", "what's happening",
    ],
    "news": [
        "news", "latest", "recent", "update", "updates",
        "today", "current", "breaking", "headlines",
        "what happened", "trending",
    ],
    "knowledge": [
        "who is", "what is", "where is", "when did", "when was",
        "how to", "how does", "how do", "why is", "why does",
        "define", "explain", "tell me about", "meaning of",
        "population of", "capital of", "founder of",
        "price of", "cost of", "weather in", "temperature in",
    ],
}


class WebSearchEngine:
    """Performs live web searches via DuckDuckGo — no API key needed."""

    def __init__(self, max_results: int = None, region: str = None, safesearch: str = None):
        self.max_results = max_results or getattr(config, "WEB_SEARCH_MAX_RESULTS", 5)
        self.region = region or getattr(config, "WEB_SEARCH_REGION", "wt-wt")
        self.safesearch = safesearch or getattr(config, "WEB_SEARCH_SAFESEARCH", "moderate")
        self.enabled = WEB_SEARCH_AVAILABLE and getattr(config, "WEB_SEARCH_ENABLED", True)
        self.search_cache = {} # {query: {"timestamp": time, "context": text}}
        self.cache_ttl = 300 # 5 minutes

    # ─── Intent Detection ───────────────────────────────────────────

    @staticmethod
    def needs_web_search(message: str) -> bool:
        """Detect if a user message would benefit from a live web search."""
        msg = message.lower().strip()

        # Skip very short greetings
        if len(msg.split()) < 3 and any(g in msg for g in ["hi", "hey", "hello", "bye", "thanks"]):
            return False

        # Check strong triggers (explicit search requests)
        for trigger in SEARCH_TRIGGERS["strong"]:
            if trigger in msg:
                return True

        # Check news triggers
        for trigger in SEARCH_TRIGGERS["news"]:
            if trigger in msg:
                return True

        # Check knowledge triggers (factual questions)
        for trigger in SEARCH_TRIGGERS["knowledge"]:
            if trigger in msg:
                return True

        # Question patterns that likely need fresh data
        if re.match(r"^(who|what|where|when|why|how|is|are|was|were|did|does|do|can|will)\b", msg):
            # Only trigger for longer questions (not "what?" or "how?")
            if len(msg.split()) >= 4:
                return True

        return False

    @staticmethod
    def extract_search_query(message: str) -> str:
        """Extract a clean search query from the user's message."""
        msg = message.strip()

        # Remove common prefixes
        prefixes = [
            "search for", "search about", "look up", "google",
            "find information about", "find info about", "find info on",
            "tell me about", "what do you know about",
            "can you search", "please search", "can you find",
            "web search for", "search the web for",
        ]
        msg_lower = msg.lower()
        for prefix in prefixes:
            if msg_lower.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break

        # Remove trailing question marks and clean up
        msg = msg.rstrip("?").strip()

        return msg if msg else message

    # ─── Search Methods ─────────────────────────────────────────────

    @retry_sync(retries=2, delay=1.0)
    def search_text(self, query: str, max_results: int = None) -> list[dict]:
        """Perform a text search and return structured results."""
        if not self.enabled:
            logger.warning("Web search not available")
            return []

        max_results = max_results or self.max_results

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    region=self.region,
                    safesearch=self.safesearch,
                    max_results=max_results,
                ))

            parsed = []
            for r in results:
                parsed.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "source": self._extract_domain(r.get("href", "")),
                })

            logger.info(f"Web search: '{query}' → {len(parsed)} results")
            return parsed

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    @retry_sync(retries=2, delay=1.0)
    def search_news(self, query: str, max_results: int = None) -> list[dict]:
        """Search specifically for news articles."""
        if not self.enabled:
            return []

        max_results = max_results or self.max_results

        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(
                    query,
                    region=self.region,
                    safesearch=self.safesearch,
                    max_results=max_results,
                ))

            parsed = []
            for r in results:
                parsed.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", r.get("link", "")),
                    "snippet": r.get("body", r.get("excerpt", "")),
                    "source": r.get("source", self._extract_domain(r.get("url", ""))),
                    "date": r.get("date", ""),
                })

            logger.info(f"News search: '{query}' → {len(parsed)} results")
            return parsed

        except Exception as e:
            logger.error(f"News search failed: {e}")
            # Fallback to text search
            return self.search_text(query + " news", max_results)

    @retry_sync(retries=2, delay=1.0)
    def scrape_url(self, url: str) -> str:
        """Fetch and extract clean text content from a URL."""
        if not SCRAPER_AVAILABLE:
            return "Scraper not available."
        
        try:
            logger.info(f"Neural Scraper: extracting {url}...")
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return "Failed to fetch URL."
            
            result = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            return result if result else "No readable content found."
        except Exception as e:
            logger.error(f"Scrape failed for {url}: {e}")
            return f"Scrape error: {str(e)}"

    # ─── Context Building ───────────────────────────────────────────

    def build_search_context(self, message: str) -> str:
        """
        Detect intent, search the web, and return a formatted context
        string ready for injection into the LLM system prompt.
        """
        if not self.enabled:
            return ""

        if not self.needs_web_search(message):
            return ""

        query = self.extract_search_query(message).lower()
        
        # --- Redundancy Suppression Layer ---
        now = datetime.now(timezone.utc).timestamp()
        if query in self.search_cache:
            cache_entry = self.search_cache[query]
            if now - cache_entry["timestamp"] < self.cache_ttl:
                logger.info(f"Redundancy Suppression: Reusing cached search for '{query}'")
                return cache_entry["context"] + "\n[Redundancy Suppression Active: Context Reused from Cache]"

        msg_lower = message.lower()

        # Decide: news search vs general search
        is_news = any(kw in msg_lower for kw in SEARCH_TRIGGERS["news"])

        if is_news:
            results = self.search_news(query)
            label = "LIVE NEWS RESULTS"
        else:
            results = self.search_text(query)
            label = "LIVE WEB SEARCH RESULTS"

        if not results:
            return ""

        # Format for LLM context
        context = f"\n--- {label} (real-time from the web) ---\n"
        context += f"Search query: \"{query}\"\n"
        context += f"Retrieved: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"

        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            snippet = r.get("snippet", "")
            source = r.get("source", "")
            date = r.get("date", "")

            # Truncate long snippets
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."

            context += f"{i}. {title}\n"
            if source:
                context += f"   Source: {source}\n"
            if date:
                context += f"   Date: {date}\n"
            if snippet:
                context += f"   {snippet}\n"
            context += "\n"

        context += f"--- END {label} ---\n"
        context += "IMPORTANT: Use the above search results to answer the user's question. "
        context += "Cite sources when possible. Do NOT say you cannot access real-time data.\n"

        # Update Cache
        self.search_cache[query] = {
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "context": context
        }

        return context

    # ─── Utilities ──────────────────────────────────────────────────

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain name from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except Exception:
            return ""
