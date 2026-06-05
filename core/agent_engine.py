"""
Agent Engine — JARVIS High-Level Orchestrator
Standardized tool execution and reasoning node.
"""
import logging
from typing import Dict, Any

from core.model_manager import ModelManager
from core.knowledge_manager import KnowledgeManager
from core.web_search import WebSearchEngine
from core.agent import AgentPipeline

logger = logging.getLogger(__name__)

class AgentEngine:
    """
    Orchestrates the AgentPipeline with standardized tool access.
    Acts as the 'Executive Prefrontal Cortex' of JARVIS.
    """

    def __init__(self, chat_engine=None, tools: Dict[str, Any] = None):
        # Initialize dependencies
        self.model_manager = ModelManager()
        self.knowledge_manager = KnowledgeManager()
        self.web_search = WebSearchEngine()
        
        # Manifest the Pipeline
        self.pipeline = AgentPipeline(
            model_manager=self.model_manager,
            knowledge_manager=self.knowledge_manager,
            web_search_engine=self.web_search
        )
        
        # Optional: Direct tool mapping override
        self.tools = tools or {}
        logger.info("Agent Node: Orchestrator Manifested.")

    def run(self, message: str, user: str = "global", conv_id: str = "default"):
        """
        Execute the multi-agent reasoning loop.
        Returns the findings to be injected into the system prompt.
        """
        logger.info(f"Agent Node: Processing request for {user} ({conv_id})")
        
        # The AgentPipeline.run returns formatted context snippets (Intel)
        intel_context = self.pipeline.run(message)
        
        return intel_context
