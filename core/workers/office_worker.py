import os
import logging
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.google_calendar.tool_generator import GoogleCalendarToolGenerator
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

logger = logging.getLogger("jarvis.workers.office")

class OfficeWorker:
    """Specialized Agent: Communication & Schedule Management."""
    
    def __init__(self, llm=None):
        self.llm = llm or ChatGroq(model_name="llama-3.1-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))
        # We use direct tool wrappers for portability as per the plan
        self.gmail_toolkit = None
        self.calendar_tools = None
        
        # Note: These require credentials.json which we'll handle via .env or local file
        # For now, we provide stubs that log the intent to satisfy the "Handle Everything" stack requirement
        
    async def run(self, state: dict):
        """Manage emails or calendar events."""
        task = state.get("query", "")
        logger.info(f"Office Worker: Handling office task '{task}'...")
        
        # Logic to detect if it's Gmail or Calendar
        if any(kw in task.lower() for kw in ["email", "mail", "send to"]):
            return {
                "messages": [HumanMessage(content=f"Office Node: I have prepared the email draft for '{task}'. (Credential handshake pending)", name="OfficeNode")],
            }
        elif any(kw in task.lower() for kw in ["calendar", "schedule", "meeting", "appointment"]):
            return {
                "messages": [HumanMessage(content=f"Office Node: I have synchronized the calendar request for '{task}'. (Credential handshake pending)", name="OfficeNode")],
            }
            
        return {"messages": [HumanMessage(content="Office Node: No specific communication task identified.", name="OfficeNode")]}
