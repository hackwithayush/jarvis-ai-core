import logging
import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import config

logger = logging.getLogger("jarvis.workers.research")

class ResearchWorker:
    """Specialized Agent: Global Intelligence & Deep Research."""
    
    def __init__(self, llm=None):
        # Default to Groq for fast, smart research if available
        self.llm = llm or ChatGroq(model_name="llama-3.1-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))
        self.search_tool = TavilySearchResults(k=5) if os.getenv("TAVILY_API_KEY") else None

    async def run(self, state: dict):
        """Execute a research mission."""
        query = state.get("query", "")
        logger.info(f"Research Worker: Investigating '{query}'...")
        
        results = []
        if self.search_tool:
            try:
                search_res = self.search_tool.invoke({"query": query})
                for res in search_res:
                    results.append(f"Source: {res['url']}\nContent: {res['content']}\n")
            except Exception as e:
                logger.error(f"Tavily Search Error: {e}")
        
        # Fallback to local scraping if search fails or is missing
        if not results:
            from core.web_search import WebSearchEngine
            ddg = WebSearchEngine()
            results.append(ddg.search_text(query, max_results=3))

        context = "\n".join(results)
        
        # Synthesize into a briefing
        prompt = ChatPromptTemplate.from_template("""
        You are the JARVIS Research Node. Synthesize the following raw intelligence into a structured briefing.
        
        QUERY: {query}
        RAW DATA: {context}
        
        GOAL: Extract the 3 most critical facts and identify the 'Strategic Implication'.
        """)
        
        chain = prompt | self.llm
        briefing = await chain.ainvoke({"query": query, "context": context})
        
        return {
            "messages": [HumanMessage(content=briefing.content, name="ResearchNode")],
            "research_data": context
        }
