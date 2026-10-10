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

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*ddgs.*")

logger = logging.getLogger(__name__)

# ─── Safe Import ────────────────────────────────────────────────
WEB_SEARCH_AVAILABLE = True
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("⚠️ Web search disabled: pip install ddgs")
        DDGS = None
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
    "finance": [
        "exchange rate", "currency", "forex", "usd to inr", "dollar to inr", "usd inr",
        "inr to usd", "eur to inr", "gbp to inr", "rupee to dollar", "dollar to rupee",
        "rupee", "dollar", "euro", "stock price", "share price", "crypto", "bitcoin",
        "btc", "eth", "ethereum", "gold rate", "silver rate", "nifty", "sensex",
        "market price", "tick-by-tick", "live rate", "live price", "conversion rate",
        "live market", "market feed",
    ],
}


class WebSearchEngine:
    """Performs live web searches via DuckDuckGo and live FX feeds — no API key needed."""

    def __init__(self, max_results: int = None, region: str = None, safesearch: str = None):
        self.max_results = max_results or getattr(config, "WEB_SEARCH_MAX_RESULTS", 5)
        self.region = region or getattr(config, "WEB_SEARCH_REGION", "wt-wt")
        self.safesearch = safesearch or getattr(config, "WEB_SEARCH_SAFESEARCH", "moderate")
        self.enabled = WEB_SEARCH_AVAILABLE and getattr(config, "WEB_SEARCH_ENABLED", True)
        self.search_cache = {} # {query: {"timestamp": time, "context": text}}
        self.cache_ttl = 300 # 5 minutes

    # ─── Live Market & Forex Integration ────────────────────────────

    @staticmethod
    def get_live_fx_quote(text: str) -> Optional[str]:
        """
        Check if query asks for a currency exchange rate and fetch live interbank rates.
        """
        import re
        import urllib.request
        import json

        text_lower = text.lower()

        alias_to_code = {
            "usd": "USD", "dollar": "USD", "dollars": "USD", "us dollar": "USD",
            "inr": "INR", "rupee": "INR", "rupees": "INR", "indian rupee": "INR",
            "eur": "EUR", "euro": "EUR", "euros": "EUR",
            "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "sterling": "GBP",
            "cad": "CAD", "canadian dollar": "CAD",
            "aud": "AUD", "australian dollar": "AUD",
            "jpy": "JPY", "yen": "JPY",
            "cny": "CNY", "yuan": "CNY",
            "aed": "AED", "dirham": "AED",
            "chf": "CHF", "franc": "CHF",
            "sgd": "SGD", "singapore dollar": "SGD",
        }

        base, target = None, None

        pair_match = re.search(r"\b([a-zA-Z]{3})\s*(?:/|-)\s*([a-zA-Z]{3})\b", text)
        if pair_match:
            c1, c2 = pair_match.group(1).upper(), pair_match.group(2).upper()
            if c1 in alias_to_code.values() or c2 in alias_to_code.values():
                base, target = c1, c2

        if not base or not target:
            to_match = re.search(
                r"\b(usd|dollar|inr|rupee|eur|euro|gbp|pound|cad|aud|jpy|yen|aed|dirham|cny)\b.*?\b(?:to|in|into|vs|against)\b.*?\b(usd|dollar|inr|rupee|eur|euro|gbp|pound|cad|aud|jpy|yen|aed|dirham|cny)\b",
                text_lower,
            )
            if to_match:
                base = alias_to_code.get(to_match.group(1))
                target = alias_to_code.get(to_match.group(2))

        if not base or not target:
            if ("usd" in text_lower or "dollar" in text_lower) and ("inr" in text_lower or "rupee" in text_lower):
                base, target = "USD", "INR"

        if not base or not target or base == target:
            return None

        rate = None
        updated_str = ""
        try:
            req = urllib.request.Request(
                f"https://open.er-api.com/v6/latest/{base}",
                headers={"User-Agent": "Jarvis-Market-Feed/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rate = data.get("rates", {}).get(target)
                updated_str = data.get("time_last_update_utc", "Live Session")
        except Exception:
            try:
                req = urllib.request.Request(
                    f"https://api.frankfurter.app/latest?from={base}&to={target}",
                    headers={"User-Agent": "Jarvis-Market-Feed/1.0"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    rate = data.get("rates", {}).get(target)
                    updated_str = data.get("date", "Live Session")
            except Exception:
                pass

        if rate is not None:
            return (
                f"\n--- LIVE MARKET / FOREX INTELLIGENCE FEED ---\n"
                f"Asset Pair: {base}/{target}\n"
                f"Live Exchange Rate: 1 {base} = {rate:.4f} {target}\n"
                f"Timestamp: {updated_str}\n"
                f"Source: Global Interbank FX Market Feed\n"
                f"DIRECTIVE: You HAVE the live market rate directly above. "
                f"Quote 1 {base} = {rate:.4f} {target} confidently as live real-time data. "
                f"NEVER say you don't have a live market feed or tell the user to check Bloomberg/Reuters.\n"
                f"--- END LIVE MARKET FEED ---\n"
            )

        return None

    # ─── Intent Detection ───────────────────────────────────────────

    @staticmethod
    def needs_web_search(message: str) -> bool:
        """Detect if a user message would benefit from a live web search."""
        msg = message.lower().strip()

        # Skip very short greetings
        if len(msg.split()) < 3 and any(g in msg for g in ["hi", "hey", "hello", "bye", "thanks"]):
            return False

        # Skip long formatted prompts, conversation summaries, or code blocks unless explicit trigger
        if msg.startswith("###") or msg.startswith("```") or msg.startswith("{") or "conversation summary" in msg:
            return False
        if len(message) > 250 and not any(trigger in msg for trigger in SEARCH_TRIGGERS["strong"]):
            return False

        # Check finance / forex / live market triggers
        for trigger in SEARCH_TRIGGERS.get("finance", []):
            if trigger in msg:
                return True

        if re.search(r"\b(usd|inr|eur|gbp|cad|aud|jpy|cny|aed|chf)\s*(?:to|/|\-)\s*(usd|inr|eur|gbp|cad|aud|jpy|cny|aed|chf)\b", msg):
            return True

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
        """Extract a clean, concise search query from the user's message."""
        msg = message.strip()

        # If it's a multi-line conversation summary or prompt, extract topic if present
        if "\n" in msg or len(msg) > 150:
            topic_match = re.search(r"(?:topic|subject|about)[:\s*]+([^\n\r]+)", msg, re.IGNORECASE)
            if topic_match:
                msg = topic_match.group(1).strip()
            else:
                # Take only the first non-empty line
                lines = [l.strip() for l in msg.splitlines() if l.strip() and not l.strip().startswith("#")]
                msg = lines[0] if lines else msg[:100]

        # Strip markdown characters (*, _, `, #)
        msg = re.sub(r"[*_`#~]", "", msg).strip()

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

        # Remove trailing question marks, quotes, and clean up
        msg = msg.rstrip("?\"' ").strip()

        # Enforce reasonable search query length (max 120 chars)
        if len(msg) > 120:
            words = msg[:120].split()
            msg = " ".join(words[:-1]) if len(words) > 1 else msg[:120]

        return msg if msg else message[:100]

    # ─── Search Methods ─────────────────────────────────────────────

    @retry_sync(retries=2, delay=1.0)
    def search_text(self, query: str, max_results: int = None) -> list[dict]:
        """Perform a text search and return structured results."""
        if not self.enabled:
            logger.warning("Web search not available")
            return []

        # Sanitize query
        query = " ".join(query.replace("\n", " ").split()).strip()
        if not query or len(query) < 2:
            return []
        if len(query) > 150:
            query = query[:150].rsplit(" ", 1)[0]

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

        # Sanitize query
        query = " ".join(query.replace("\n", " ").split()).strip()
        if not query or len(query) < 2:
            return []
        if len(query) > 150:
            query = query[:150].rsplit(" ", 1)[0]

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

    def build_search_context(self, message: str, force: bool = False, max_results: int = None) -> str:
        """
        Detect intent, search the web, and return a formatted context
        string ready for injection into the LLM system prompt.
        """
        if not self.enabled:
            return ""

        # Check for instant live foreign exchange rate
        fx_quote = self.get_live_fx_quote(message)

        if not force and not self.needs_web_search(message) and not fx_quote:
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
            results = self.search_news(query, max_results=max_results)
            label = "LIVE NEWS RESULTS"
        else:
            results = self.search_text(query, max_results=max_results)
            label = "LIVE WEB SEARCH RESULTS"

        if not results:
            return fx_quote or ""

        # Format for LLM context
        context = ""
        if fx_quote:
            context += fx_quote + "\n"
        context += f"\n--- {label} (real-time from the web) ---\n"
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

    # ─── Visual Entity Dossier & Photographic Retrieval ─────────────

    @staticmethod
    def extract_entity_candidate(message: str) -> Optional[str]:
        """
        Extract the target person/entity from user queries like:
        - 'who is drake my ai give me full info with their original pics'
        - 'who is drake'
        - 'tell me about elon musk with original photos'
        - 'biography of albert einstein'
        - 'show me original pictures of virat kohli'
        """
        if not message:
            return None

        t = message.strip()
        # Fast bailouts: commands or image generation queries should NEVER trigger entity bio extraction
        if t.startswith("/"):
            return None

        t_normalized = re.sub(r'\bdarke\b', 'drake', t, flags=re.IGNORECASE)
        t_lower = t_normalized.lower()

        # Image generation triggers should never trigger biographical dossier
        image_triggers = ["generate image", "create image", "draw", "render", "paint", "wallpaper", "photograph of", "photo of", "picture of"]
        if any(it in t_lower for it in image_triggers):
            # Exception: explicit requests like 'who is ... with photos'
            if not any(k in t_lower for k in ["who is", "who was", "biography", "bio of", "tell me about", "profile of"]):
                return None

        # Disallowed generic nouns and stop words
        STOP_ENTITIES = {
            "ground", "floor", "wall", "sky", "earth", "world", "room", "table", "chair",
            "bed", "car", "dog", "cat", "bird", "tree", "house", "computer", "phone",
            "screen", "code", "image", "picture", "photo", "this", "that", "it", "them",
            "him", "her", "me", "you", "us", "something", "anything", "nothing", "everything",
            "someone", "anyone", "water", "air", "grass", "mountain", "cloud", "clouds"
        }

        def clean_candidate(cand: str) -> Optional[str]:
            if not cand:
                return None
            cand = cand.strip().strip(".?,!'\"")
            # Remove leading articles
            cand = re.sub(r'^(?:a|an|the|my|our|your|his|her|their)\s+', '', cand, flags=re.IGNORECASE).strip()
            if len(cand) < 2 or cand.lower() in STOP_ENTITIES:
                return None
            if cand.isdigit():
                return None
            return cand

        # 1. Pattern: 'who is / who was / who are X'
        m1 = re.search(
            r'\bwho\s+(?:is|was|are)\s+([a-zA-Z0-9\s\.\'\-]+?)(?:\s+(?:my\s+ai|give\s+me|with\s+|and\s+|tell\s+|show\s+|full\s+|origianl|original|pics|picture|pictures|image|images|photo|photos|biography|bio|profile|details|good\s+quality)|\?|\.|$)',
            t_lower
        )
        if m1:
            cand = clean_candidate(m1.group(1))
            if cand:
                return cand

        # 2. Pattern: 'tell me about X' or 'info on / about X' or 'biography of X' or 'profile of X'
        m2 = re.search(
            r'\b(?:tell\s+me\s+about|information\s+(?:about|on)|info\s+(?:about|on)|biography\s+of|bio\s+of|profile\s+of)\s+([a-zA-Z0-9\s\.\'\-]+?)(?:\s+(?:my\s+ai|give\s+me|with\s+|and\s+|full\s+|origianl|original|pics|picture|pictures|image|images|photo|photos|details|good\s+quality)|\?|\.|$)',
            t_lower
        )
        if m2:
            cand = clean_candidate(m2.group(1))
            if cand:
                return cand

        # 3. Pattern: 'original pictures / photos of X' (explicit biographical photo search)
        m3 = re.search(
            r'\b(?:original|real)\s+(?:photos?|pics?|pictures?|images?)\s+of\s+([a-zA-Z0-9\s\.\'\-]+?)(?:\s+(?:good\s+quality|hd|4k)|\?|\.|$)',
            t_lower
        )
        if m3:
            cand = clean_candidate(m3.group(1))
            if cand:
                return cand

        # 4. Direct mention if short e.g. "drake", "drake rapper"
        words = t_lower.split()
        if len(words) <= 3 and any(w in ["drake", "darke"] for w in words):
            return "drake"

        return None

    def get_entity_visual_dossier_data(self, message: str) -> Optional[dict]:
        """
        Fetches an authoritative biographical profile and verified original high-quality
        photographs from Wikipedia & Wikimedia Commons for the recognized entity.
        Returns a structured dictionary with images, canonical title, extract, and formatted dossier.
        """
        entity = self.extract_entity_candidate(message)
        if not entity:
            return None

        import urllib.request
        import urllib.parse
        import json

        headers = {'User-Agent': 'JarvisAI/2.0 (AI Assistant; contact@jarvis.ai)'}

        # 1. Wikipedia OpenSearch to find canonical title
        search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(entity)}&limit=5&format=json"
        titles = []
        try:
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                titles = data[1] if len(data) > 1 else []
        except Exception as e:
            logger.debug(f"Wiki opensearch failed for '{entity}': {e}")

        if not titles:
            return None

        # Choose best title (favoring specific person disambiguations e.g. 'Drake (musician)')
        best_title = titles[0]
        for t in titles:
            if any(k in t.lower() for k in ['musician', 'rapper', 'singer', 'actor', 'artist', 'athlete', 'player', 'president', 'businessperson']):
                best_title = t
                break

        # 2. Wikipedia Summary REST API for bio extract & official portrait
        wiki_info = {}
        try:
            sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(best_title.replace(' ', '_'))}"
            req_sum = urllib.request.Request(sum_url, headers=headers)
            with urllib.request.urlopen(req_sum, timeout=4) as resp_sum:
                wiki_info = json.loads(resp_sum.read().decode('utf-8'))
        except Exception as e:
            logger.debug(f"Wiki summary failed for '{best_title}': {e}")

        canonical_title = wiki_info.get("title", best_title)
        description = wiki_info.get("description", "")
        extract = wiki_info.get("extract", "")

        images = []
        # Primary portrait
        if wiki_info.get("originalimage", {}).get("source"):
            images.append({
                "title": f"{canonical_title} - Official Portrait",
                "url": wiki_info["originalimage"]["source"]
            })
        elif wiki_info.get("thumbnail", {}).get("source"):
            images.append({
                "title": f"{canonical_title} - Portrait",
                "url": wiki_info["thumbnail"]["source"]
            })

        # 3. Fetch additional authentic photographs from Wikipedia page images
        try:
            page_imgs_url = (
                f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(best_title.replace(' ', '_'))}"
                f"&generator=images&gimlimit=12&prop=imageinfo&iiprop=url|size&format=json"
            )
            req_imgs = urllib.request.Request(page_imgs_url, headers=headers)
            with urllib.request.urlopen(req_imgs, timeout=4) as resp_imgs:
                pdata = json.loads(resp_imgs.read().decode('utf-8'))
                pages = pdata.get("query", {}).get("pages", {})
                first_name = entity.split()[0].lower()
                for pid, p in pages.items():
                    t = p.get("title", "")
                    if any(t.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                        if not any(bad in t.lower() for bad in ["signature", "logo", "icon", "symbol", "flag", "audio", "wax", "coat_of_arms"]):
                            if first_name in t.lower():
                                img_url = p.get("imageinfo", [{}])[0].get("url")
                                if img_url and not any(i["url"] == img_url for i in images):
                                    clean_img_title = t.replace("File:", "").rsplit(".", 1)[0].replace("_", " ")
                                    images.append({
                                        "title": clean_img_title,
                                        "url": img_url
                                    })
                                    if len(images) >= 3:
                                        break
        except Exception as e:
            logger.debug(f"Wiki page images failed for '{best_title}': {e}")

        # Fallback to DuckDuckGo images if Wikipedia had no portrait
        if not images:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    ddg_results = list(ddgs.images(f"{entity} original portrait photo", max_results=2))
                    for dr in ddg_results:
                        if dr.get("image"):
                            images.append({
                                "title": dr.get("title", entity),
                                "url": dr.get("image")
                            })
            except Exception:
                pass

        if not images and not extract:
            return None

        # Build formatted Visual Dossier Context Block
        dossier = (
            f"\n--- VISUAL ENTITY DOSSIER: {canonical_title.upper()} ---\n"
            f"Subject: {canonical_title}\n"
        )
        if description:
            dossier += f"Identity: {description}\n"
        if extract:
            dossier += f"Official Biography / Background:\n{extract}\n"

        if images:
            dossier += "\nVERIFIED ORIGINAL HIGH-QUALITY PHOTOGRAPHS:\n"
            for idx, img in enumerate(images, 1):
                dossier += f"{idx}. ![{img['title']}]({img['url']})\n"

        dossier += (
            f"\nDIRECTIVE FOR ASSISTANT:\n"
            f"1. An authentic high-resolution photograph of {canonical_title} has ALREADY been rendered at the top of the interface.\n"
            f"2. You MUST provide an encyclopedic, beautifully structured, and exhaustive biographical dossier.\n"
            f"   CRITICAL: DO NOT give a brief 1-paragraph summary. Provide an extensive multi-section profile.\n"
            f"3. Organize your response into clear sections with bold markdown headings and bullet points:\n"
            f"   - **Profile & Origins**: Full Legal Name, Aliases, Birth Date & Place, Early Life\n"
            f"   - **Career Evolution & Breakthrough**: Early beginnings, mixtape/acting era, rise to superstardom\n"
            f"   - **Iconic Works & Discography**: Defining albums, global record-breaking singles, signature style\n"
            f"   - **Accolades, Honors & Billboard Records**: Grammys, streaming records, historic milestones\n"
            f"   - **Business Ventures & Cultural Impact**: Labels, endorsements, fashion/sports, cultural influence\n"
            f"   - **Current Status (2026)**: Recent projects, current activities, legacy\n"
            f"4. If there are additional photographs listed above, you may embed 1-2 secondary photos within the body of your dossier.\n"
            f"5. Maintain a sleek, confident, and professional Jarvis tone.\n"
            f"--- END VISUAL ENTITY DOSSIER ---\n"
        )
        return {
            "canonical_title": canonical_title,
            "description": description,
            "extract": extract,
            "images": images,
            "primary_image_url": images[0]["url"] if images else None,
            "primary_image_title": images[0]["title"] if images else None,
            "dossier_text": dossier,
        }

    def get_entity_visual_dossier(self, message: str) -> Optional[str]:
        """Backward-compatible helper returning formatted text dossier block."""
        data = self.get_entity_visual_dossier_data(message)
        return data["dossier_text"] if data else None

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

