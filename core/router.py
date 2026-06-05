"""
Jarvis v5.0 — Intelligent Router
Automated model selection based on intent detection.
"""
from typing import List, Dict
import config

class SmartRouter:
    """Manages model selection for production intelligence tasks."""

    CODE_KEYWORDS = ["python", "javascript", "code", "function", "sql", "html", "css", "script", "debug", "refactor"]
    
    @staticmethod
    def select_model(message: str) -> str:
        """Select the optimal model for a given user prompt."""
        msg_lower = message.lower()
        
        # 1. Coding Task (Highest Priority)
        if any(kw in msg_lower for kw in SmartRouter.CODE_KEYWORDS):
            return config.ROUTING_CONFIG.get("coding", "qwen2.5-coder:7b")
        
        # 2. Short/Fast Query
        if len(message.split()) < 8:
            return config.ROUTING_CONFIG.get("fast", "phi3:mini")
            
        # 3. Default General Intelligence
        return config.ROUTING_CONFIG.get("reasoning", "qwen2.5:7b")

    @staticmethod
    def get_fallback_model() -> str:
        """Emergency model for system resiliency."""
        return "phi3:mini"
