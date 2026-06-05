import requests
import json
import logging
import config
from core.model_manager import ModelManager

logger = logging.getLogger("jarvis.instagram")

class InstagramEngine:
    """
    JARVIS Instagram Creator AI Node.
    Handles semi-automated growth, analytics, and content ideation using the Instagram Graph API.
    Does NOT auto-post or DM (avoids bans). Focuses on high-value intelligence.
    """
    
    def __init__(self):
        self.access_token = config.INSTAGRAM_ACCESS_TOKEN
        self.user_id = config.INSTAGRAM_USER_ID
        self.model = ModelManager()
        self.base_url = "https://graph.facebook.com/v19.0"
        
    def _is_configured(self) -> bool:
        return bool(self.access_token and self.user_id)

    def fetch_recent_posts(self, limit: int = 10):
        """Fetch recent media from Instagram via Graph API."""
        if not self._is_configured():
            return {"status": "error", "message": "Instagram API not configured in .env"}
            
        url = f"{self.base_url}/{self.user_id}/media"
        params = {
            "fields": "id,caption,media_type,like_count,comments_count,timestamp,permalink",
            "access_token": self.access_token,
            "limit": limit
        }
        
        try:
            logger.info("Instagram Node: Fetching recent media data.")
            response = requests.get(url, params=params)
            data = response.json()
            
            if "error" in data:
                logger.error(f"IG API Error: {data['error']}")
                return {"status": "error", "message": data["error"].get("message", "Unknown API Error")}
                
            return {"status": "success", "data": data.get("data", [])}
        except Exception as e:
            logger.error(f"Instagram Fetch Failure: {e}")
            return {"status": "error", "message": str(e)}

    def analyze_performance(self) -> str:
        """Fetch posts and run neural analytics on performance."""
        if not self._is_configured():
            # Run a simulated analysis if keys aren't set yet (for demonstration)
            return self._mock_analysis()
            
        result = self.fetch_recent_posts()
        if result["status"] == "error":
            return f"❌ **Instagram Grid Error**: {result['message']}\n_Please check your Graph API keys._"
            
        posts = result["data"]
        if not posts:
            return "⚠️ No posts found on your account."
            
        # Compile raw data
        total_likes = 0
        total_comments = 0
        media_stats = {"IMAGE": {"count": 0, "eng": 0}, "VIDEO": {"count": 0, "eng": 0}, "CAROUSEL_ALBUM": {"count": 0, "eng": 0}}
        
        post_summaries = []
        for post in posts:
            likes = post.get("like_count", 0)
            comments = post.get("comments_count", 0)
            m_type = post.get("media_type", "IMAGE")
            eng = likes + comments
            
            total_likes += likes
            total_comments += comments
            
            if m_type in media_stats:
                media_stats[m_type]["count"] += 1
                media_stats[m_type]["eng"] += eng
                
            caption_preview = post.get("caption", "")[:30].replace("\n", " ") + "..."
            post_summaries.append(f"[{m_type}] Eng: {eng} | Cap: {caption_preview}")
            
        avg_eng = (total_likes + total_comments) / len(posts)
        
        # Ask LLM to generate actionable advice
        prompt = f"""
        Act as an elite Instagram Growth Strategist. Analyze the following raw data from my latest {len(posts)} posts:
        
        - Average Engagement: {avg_eng:.1f}
        - Total Likes: {total_likes}
        - Total Comments: {total_comments}
        
        Breakdown by Media Type:
        {json.dumps(media_stats)}
        
        Recent Posts:
        {chr(10).join(post_summaries)}
        
        Provide:
        1. A brief summary of what's working.
        2. 3 highly actionable, semi-automated growth suggestions (e.g., best times to post, caption length, hashtag strategy).
        3. Specifically tailor advice assuming I post Anime Content / Edits.
        Keep it concise, formatted with markdown, and use an intelligent Jarvis-like tone.
        """
        
        logger.info("Instagram Node: Generating neural growth insights.")
        insights = self.model.generate(
            prompt=prompt,
            model=config.ROUTING_CONFIG["reasoning"],
            system_prompt="You are JARVIS's Social Media Growth Node."
        )
        
        return f"📊 *Instagram Neural Analytics*\n\n{insights}"

    def generate_viral_ideas(self) -> str:
        """Generate anime-specific viral content ideas."""
        prompt = """
        Generate 3 highly viral, trending Instagram Reel concepts specifically for Anime edits (e.g., Naraka, Jujutsu Kaisen, Demon Slayer).
        For each idea provide:
        - Hook (First 3 seconds)
        - Audio style (e.g., specific trending phonk or lofi track)
        - Visual pacing (e.g., fast cuts on beat)
        - 3-5 hyper-targeted hashtags (e.g., #animeedit #naraka)
        Format as a clean, actionable list.
        """
        logger.info("Instagram Node: Synthesizing viral anime content concepts.")
        ideas = self.model.generate(
            prompt=prompt,
            model=config.ROUTING_CONFIG["chat"],
            system_prompt="You are JARVIS's Content Ideation Engine."
        )
        return f"🔥 *Viral Anime Content Generator*\n\n{ideas}"

    def draft_caption(self, topic: str) -> str:
        """Draft a high-converting caption with hashtags."""
        prompt = f"""
        Write a highly engaging Instagram caption for a post about: "{topic}".
        Include:
        1. A strong hook to stop scrolling.
        2. A Call to Action (CTA) to drive comments or shares.
        3. 8-10 highly relevant, trending hashtags (anime/edit focused if applicable).
        Keep the layout clean and easy to read.
        """
        caption = self.model.generate(
            prompt=prompt,
            model=config.ROUTING_CONFIG["fast"]
        )
        return f"📝 *Drafted Caption*\n\n{caption}"

    def _mock_analysis(self) -> str:
        """Simulated analysis when API keys are not provided."""
        return (
            "📊 *Instagram Neural Analytics (Simulated)*\n\n"
            "⚠️ _Graph API keys not detected. Displaying demo insights._\n\n"
            "**Data Scan (Last 10 Posts):**\n"
            "• Average Engagement: `842`\n"
            "• Best Format: `REELS` (3x higher reach than static images)\n\n"
            "**Growth Directives:**\n"
            "1. **Pacing:** Your fast-cut anime edits are outperforming slow scenes. Stick to 140+ BPM trending audio.\n"
            "2. **Timing:** Post between 7:00 PM and 9:00 PM EST for maximum initial algorithmic push.\n"
            "3. **Captions:** Your current captions are too long. Shift to short hooks (e.g., 'Who wins this 1v1?') to drive comments."
        )
