"""
News Fetcher — RSS Feed Parser & Web Scraper
Fetches news articles from multiple sources for the knowledge base.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# User agent for web requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}


class NewsFetcher:
    """Fetches news from RSS feeds and web sources."""

    def __init__(self):
        self.feeds = config.RSS_FEEDS
        self._seen_urls = set()

    # ─── RSS Feed Fetching ──────────────────────────────────────────

    def fetch_all_feeds(self) -> list[dict]:
        """Fetch articles from all configured RSS feeds."""
        all_articles = []

        for source_name, feed_url in self.feeds.items():
            try:
                articles = self._fetch_feed(feed_url, source_name)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {source_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch {source_name}: {e}")

        # Deduplicate by URL
        unique_articles = []
        seen = set()
        for article in all_articles:
            url = article.get("url", "")
            if url and url not in seen:
                seen.add(url)
                unique_articles.append(article)

        logger.info(f"Total unique articles fetched: {len(unique_articles)}")
        return unique_articles

    def _fetch_feed(self, feed_url: str, source_name: str) -> list[dict]:
        """Fetch and parse a single RSS feed."""
        articles = []
        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning(f"Feed parse error for {source_name}: {feed.bozo_exception}")
                return []

            for entry in feed.entries[:20]:  # Limit per source
                article = self._parse_entry(entry, source_name)
                if article:
                    articles.append(article)

        except Exception as e:
            logger.error(f"Feed fetch error for {source_name}: {e}")

        return articles

    def _parse_entry(self, entry, source_name: str) -> Optional[dict]:
        """Parse a single feed entry into a structured article."""
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Get link
        link = entry.get("link", "")

        # Skip if already seen
        if link in self._seen_urls:
            return None
        self._seen_urls.add(link)

        # Get summary/description
        summary = ""
        if hasattr(entry, "summary"):
            summary = self._clean_html(entry.summary)
        elif hasattr(entry, "description"):
            summary = self._clean_html(entry.description)

        # Get content if available
        content = ""
        if hasattr(entry, "content"):
            for c in entry.content:
                content += self._clean_html(c.get("value", ""))

        # Get published date
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                published = datetime.now(timezone.utc).isoformat()
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                published = datetime.now(timezone.utc).isoformat()
        else:
            published = datetime.now(timezone.utc).isoformat()

        # Get categories/tags
        categories = []
        if hasattr(entry, "tags"):
            categories = [t.get("term", "") for t in entry.tags if t.get("term")]

        # Build full content
        full_content = f"Title: {title}\n\n"
        if content:
            full_content += content
        elif summary:
            full_content += summary
        else:
            full_content += title

        # Determine category
        category = self._categorize(title, summary, categories, source_name)

        return {
            "title": title,
            "content": full_content,
            "url": link,
            "source": source_name,
            "category": category,
            "timestamp": published,
            "tags": categories,
        }

    # ─── Web Article Extraction ─────────────────────────────────────

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch and extract main content from a web article URL."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # Remove unwanted elements
            for tag in soup.find_all(["script", "style", "nav", "footer", "aside", "iframe"]):
                tag.decompose()

            # Try to find main content
            main_content = None
            for selector in ["article", "main", '[role="main"]', ".post-content", ".article-body"]:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
            else:
                # Fallback: get all paragraph text
                paragraphs = soup.find_all("p")
                text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)

            # Clean up
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)

            return text if len(text) > 100 else None

        except Exception as e:
            logger.debug(f"Failed to extract article from {url}: {e}")
            return None

    # ─── Wikipedia Current Events ───────────────────────────────────

    def fetch_wikipedia_current_events(self) -> list[dict]:
        """Fetch current events from Wikipedia."""
        articles = []
        try:
            today = datetime.now(timezone.utc)
            url = f"https://en.wikipedia.org/wiki/Portal:Current_events/{today.strftime('%B_%Y')}"

            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "lxml")

            # Find event entries
            events = soup.select(".description")
            if not events:
                events = soup.select("ul li")

            for event in events[:30]:
                text = event.get_text(strip=True)
                if len(text) > 30:
                    articles.append({
                        "title": f"Current Event: {text[:100]}",
                        "content": text,
                        "source": "Wikipedia Current Events",
                        "category": "world",
                        "timestamp": today.isoformat(),
                    })

            logger.info(f"Fetched {len(articles)} Wikipedia current events")
        except Exception as e:
            logger.warning(f"Failed to fetch Wikipedia events: {e}")

        return articles

    # ─── Utilities ──────────────────────────────────────────────────

    @staticmethod
    def _clean_html(html_text: str) -> str:
        """Remove HTML tags and clean text."""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "lxml")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def _categorize(title: str, summary: str, tags: list, source: str) -> str:
        """Categorize an article based on content and source."""
        combined = f"{title} {summary} {' '.join(tags)} {source}".lower()

        categories = {
            "technology": ["tech", "software", "hardware", "ai", "artificial intelligence",
                           "startup", "google", "apple", "microsoft", "cyber", "data",
                           "programming", "code", "developer", "app", "digital"],
            "science": ["science", "research", "study", "discovery", "space", "nasa",
                        "physics", "biology", "chemistry", "medical", "health", "climate"],
            "business": ["business", "economy", "market", "stock", "finance", "trade",
                         "company", "revenue", "profit", "investment", "crypto", "bitcoin"],
            "world": ["war", "conflict", "election", "government", "politics", "country",
                      "president", "minister", "diplomacy", "united nations", "military"],
            "sports": ["sports", "football", "cricket", "basketball", "tennis", "olympics",
                       "tournament", "league", "championship", "match", "game"],
        }

        scores = {cat: 0 for cat in categories}
        for cat, keywords in categories.items():
            for keyword in keywords:
                if keyword in combined:
                    scores[cat] += 1

        best_cat = max(scores, key=scores.get)
        return best_cat if scores[best_cat] > 0 else "general"

    def reset_seen(self):
        """Reset the seen URLs cache."""
        self._seen_urls.clear()
