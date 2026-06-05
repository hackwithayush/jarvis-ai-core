import logging
import asyncio
import feedparser
import config
import uuid
from datetime import datetime
from core.mission_engine import MissionEngine
from core.briefing_engine import BriefingEngine

logger = logging.getLogger("jarvis.intel")

class IntelEngine:
    """World Intelligence Node: Autonomous News Synthesis & AI Analysis."""
    
    def __init__(self, mission_engine: MissionEngine, chat_engine, briefing_engine: BriefingEngine):
        self.mission_engine = mission_engine
        self.chat_engine = chat_engine
        self.briefing_engine = briefing_engine
        self.archive = []

    async def fetch_world_trends(self):
        """Aggregate top headlines from global RSS feeds."""
        logger.info("Syncing with Global News Nodes...")
        headlines = []
        for name, url in config.RSS_FEEDS.items():
            try:
                feed = await asyncio.get_event_loop().run_in_executor(None, lambda: feedparser.parse(url))
                if feed.entries:
                    # Take top 1 from each major feed for high-density analysis
                    for entry in feed.entries[:1]:
                        headlines.append(f"[{name}] {entry.title}")
            except Exception as e:
                logger.error(f"Failed to fetch {name}: {e}")
        
        return "\n".join(headlines)

    async def create_world_report(self, region="Global"):
        """Orchestrate an AI-analyzed intelligence report and briefing PDF."""
        trends_raw = await self.fetch_world_trends()
        if not trends_raw:
            return {"status": "error", "message": "No live intelligence gathered."}

        # 1. AI Trend Analysis
        analysis_prompt = f"""Analyze these top global news headlines and generate a structured intelligence briefing.
Headlines:
{trends_raw}

Return a JSON-like structure (but as text) with:
1. SUMMARY: A 2-sentence executive summary of the global state.
2. TOP_TRENDS: List 3 key trends, each with a 'title' and 'implication' (why it matters to a tech visionary like Stark).
"""
        analysis_response = self.chat_engine.generate_direct(analysis_prompt)
        
        # 2. Extract Data (Simple parsing)
        report_id = uuid.uuid4().hex[:8]
        summary = "Global neural nodes stabilized. Analysis in progress."
        trends = []
        
        try:
            # Basic parsing of the LLM response
            if "SUMMARY:" in analysis_response:
                summary = analysis_response.split("SUMMARY:")[1].split("TOP_TRENDS:")[0].strip()
            
            # Simple trend extraction
            if "TOP_TRENDS:" in analysis_response:
                lines = analysis_response.split("TOP_TRENDS:")[1].split("\n")
                current_trend = None
                for line in lines:
                    line = line.strip()
                    if line.startswith("-") or (line and line[0].isdigit()):
                        if ":" in line:
                            title, impl = line.split(":", 1)
                            trends.append({
                                "title": title.strip("- ").strip(),
                                "implication": impl.strip()
                            })
        except:
            logger.warning("AI Analysis parsing partially failed. Using raw data.")

        # 3. Generate PDF Briefing
        report_data = {
            "id": report_id,
            "topic": f"World Intelligence: {region}",
            "summary": summary,
            "trends": trends[:3]
        }
        
        pdf_filename = self.briefing_engine.generate_pdf(report_data)
        
        # 4. Trigger Multimedia Summary
        mission_prompt = f"Create a high-impact briefing video based on this intelligence: {summary} Key Trends: {trends_raw}"
        mission_id = self.mission_engine.create_mission(mission_prompt)
        
        report = {
            "id": report_id,
            "mission_id": mission_id,
            "topic": f"World Intel: {region}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "In Progress",
            "pdf_url": f"/api/intel/download/{pdf_filename}" if pdf_filename else None,
            "summary": summary
        }
        self.archive.append(report)
        return report

    def get_archive(self):
        return self.archive
