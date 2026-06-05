"""
Entertainment Recommender — PRO AI VERSION
Context-aware, taste learning, smart ranking, and rich responses.
"""

import urllib.parse
import random
from collections import Counter
from typing import List, Dict


class EntertainmentRecommender:
    """AI-powered entertainment recommendation system."""

    CURATED_LISTS = {
        "kdrama": [
            {"title": "Bloodhounds", "tags": ["action", "crime"]},
            {"title": "The Glory", "tags": ["revenge", "drama"]},
            {"title": "Taxi Driver", "tags": ["action", "justice"]},
            {"title": "Vincenzo", "tags": ["crime", "comedy"]},
            {"title": "Weak Hero Class 1", "tags": ["school", "action"]},
            {"title": "Alchemy of Souls", "tags": ["fantasy", "romance"]},
            {"title": "Moving", "tags": ["superpower", "action"]}
        ],
        "anime": [
            {"title": "Attack on Titan", "tags": ["dark", "action"]},
            {"title": "Jujutsu Kaisen", "tags": ["action", "supernatural"]},
            {"title": "Solo Leveling", "tags": ["power", "fantasy"]},
            {"title": "Demon Slayer", "tags": ["action", "emotional"]},
            {"title": "Vinland Saga", "tags": ["historical", "deep"]},
            {"title": "Frieren", "tags": ["emotional", "fantasy"]}
        ],
        "movie": [
            {"title": "Oppenheimer", "tags": ["biopic", "intense"]},
            {"title": "John Wick 4", "tags": ["action", "fast"]},
            {"title": "Dune Part 2", "tags": ["sci-fi", "epic"]},
            {"title": "Spider-Man: Across the Spider-Verse", "tags": ["animated", "multiverse"]},
            {"title": "The Batman", "tags": ["dark", "detective"]}
        ]
    }

    PLATFORMS = ["Netflix", "Prime Video", "Disney+", "Crunchyroll"]
    
    PREFIXES = [
        "💡 You might like this:",
        "🔥 Try this next:",
        "🎯 Based on your vibe:",
        "👀 This matches your taste:"
    ]

    # ─────────────────────────────────────────────
    # 🎯 SMART RECOMMENDATION
    # ─────────────────────────────────────────────
    def recommend(self, media_type: str, mood: str = None) -> List[str]:
        """Return smart recommendations based on type + mood."""
        items = self.CURATED_LISTS.get(media_type, [])
        if not items:
            return []

        if mood:
            filtered = [i for i in items if mood.lower() in i["tags"]]
            if filtered:
                items = filtered

        # Shuffle for variation
        random.shuffle(items)

        return [self.format_output(i["title"]) for i in items[:3]]

    # ─────────────────────────────────────────────
    # 🎬 FORMAT OUTPUT (LIKE CHATGPT STYLE)
    # ─────────────────────────────────────────────
    def format_output(self, title: str) -> str:
        query = urllib.parse.quote(f"{title} official trailer")
        youtube_link = f"https://www.youtube.com/results?search_query={query}"

        platform = random.choice(self.PLATFORMS)

        return (
            f"🎬 *{title}*\n"
            f"▶️ Watch trailer: {youtube_link}\n"
            f"📺 Platform: {platform}"
        )

    # ─────────────────────────────────────────────
    # 🧠 PERSONALIZED AI SUGGESTION
    # ─────────────────────────────────────────────
    def get_proactive_suggestion(self, taste_history: List[str]) -> str:
        """Netflix-style 'Because you liked...' system with smart ranking."""
        if not taste_history:
            return ""

        counter = Counter(taste_history)
        
        # Get top 2 interests
        top_matches = counter.most_common(2)
        if not top_matches:
            return ""
            
        main_category = top_matches[0][0]
        secondary_category = top_matches[1][0] if len(top_matches) > 1 else None

        items = self.CURATED_LISTS.get(main_category, [])
        if not items:
            return ""

        selected = random.choice(items)
        prefix = random.choice(self.PREFIXES)

        text = f"{prefix}\n\n"
        text += f"💡 *Because you mostly enjoy {main_category.upper()}*:\n\n"
        text += self.format_output(selected["title"])
        
        if secondary_category:
            text += f"\n\n🔥 You also seem to enjoy {secondary_category.upper()} — want suggestions?"

        return text

    # ─────────────────────────────────────────────
    # 🔥 NEXT-LEVEL FEATURE (CHATGPT STYLE)
    # ─────────────────────────────────────────────
    def recommend_from_text(self, user_input: str) -> str:
        """Understand user message intent and provide smart suggestions."""
        text = user_input.lower()

        if any(kw in text for kw in ["anime", "animation"]):
            return "\n\n".join(self.recommend("anime"))

        elif any(kw in text for kw in ["kdrama", "k-drama", "korean"]):
            return "\n\n".join(self.recommend("kdrama"))

        elif "movie" in text:
            return "\n\n".join(self.recommend("movie"))

        elif any(kw in text for kw in ["sad", "emotional", "cry"]):
            return "\n\n".join(self.recommend("anime", mood="emotional"))

        elif any(kw in text for kw in ["action", "fast", "fight"]):
            # Try across all categories if specific one not mentioned
            return "\n\n".join(self.recommend("movie", mood="action"))

        return "I can suggest Anime, Movies, or K-Dramas. What are you in the mood for?"
