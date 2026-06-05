import logging
import os
from playwright.async_api import async_playwright
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

logger = logging.getLogger("jarvis.workers.browser")

class BrowserWorker:
    """Specialized Agent: Autonomous Web Browsing & Visual Extraction."""
    
    def __init__(self, llm=None):
        self.llm = llm or ChatGroq(model_name="llama-3.1-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))

    async def run(self, state: dict):
        """Navigate a URL and extract specific data."""
        url = state.get("url")
        objective = state.get("objective", "Extract main content")
        
        if not url:
            return {"error": "No target URL provided to Browser Node."}

        logger.info(f"Browser Worker: Navigating to {url} to {objective}...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle")
                # Wait for any dynamic content
                await page.wait_for_timeout(2000)
                
                # Use LLM to decide what to extract if it's complex, 
                # but for v1 we just get text
                content = await page.content()
                text = await page.evaluate("document.body.innerText")
                
                # Cleanup
                text_clean = " ".join(text.split())[:8000]
                
                summary_prompt = f"Summarize this webpage content specifically for this objective: {objective}\n\nCONTENT:\n{text_clean}"
                summary = await self.llm.ainvoke(summary_prompt)
                
                await browser.close()
                return {
                    "messages": [HumanMessage(content=summary.content, name="BrowserNode")],
                    "url": url,
                    "extracted_text": text_clean
                }
            except Exception as e:
                logger.error(f"Playwright Error: {e}")
                await browser.close()
                return {"error": f"Browser node failed: {e}"}
