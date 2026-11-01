import logging
import os
from langchain_core.messages import HumanMessage
from core.browser_engine import browser_engine

logger = logging.getLogger("jarvis.workers.browser")

class BrowserWorker:
    """Specialized Agent: Autonomous Web Browsing & Visual Extraction using Browser-Use."""
    
    def __init__(self, llm=None):
        self.llm = llm

    async def run(self, state: dict):
        """Navigate web, interact with pages, and fulfill autonomous web objectives."""
        url = state.get("url")
        objective = state.get("objective")
        query = state.get("user_query") or state.get("task")
        
        # Build comprehensive natural language browser directive
        if url and objective:
            task = f"Navigate to {url} and {objective}."
        elif url:
            task = f"Navigate to {url} and extract the primary contents and answers."
        elif objective:
            task = objective
        elif query:
            task = query
        else:
            return {"error": "No web target or objective provided to Browser Node."}

        logger.info(f"Browser Worker: Dispatching autonomous task -> '{task}'")
        
        # Use our high-level BrowserEngine powered by Browser-Use
        try:
            res = await browser_engine.execute_task_async(
                task=task,
                headless=False, # Allow user to see Tony Stark HUD in action, or set headless=True
                timeout=120
            )
            
            if res.get("status") == "success":
                final_text = res.get("final_result", "Web automation task completed successfully.")
                return {
                    "messages": [HumanMessage(content=final_text, name="BrowserNode")],
                    "url": url,
                    "urls_visited": res.get("urls_visited", []),
                    "extracted_text": final_text
                }
            else:
                err = res.get("error", "Unknown browser automation failure.")
                logger.error(f"Browser Worker execution reported error: {err}")
                return {
                    "messages": [HumanMessage(content=f"Browser automation encountered an issue: {err}", name="BrowserNode")],
                    "error": err
                }
        except Exception as e:
            logger.exception(f"Browser Worker critical fault: {e}")
            return {"error": f"Browser node failed: {e}"}
