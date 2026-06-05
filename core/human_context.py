import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HumanContextManager:
    """Manages semantic memory about the user to provide emotional continuity and companionship."""
    def __init__(self):
        self.memory_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)
            
        self.context_file = os.path.join(self.memory_dir, "human_context.json")
        self.context: Dict[str, Any] = self._load_context()
        
    def _load_context(self) -> Dict[str, Any]:
        if os.path.exists(self.context_file):
            try:
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load human context: {e}")
                
        return {
            "routines": {},
            "emotional_patterns": {
                "current_stress_level": "balanced",
                "recent_triggers": []
            },
            "active_projects": ["JARVIS OS Architecture"],
            "last_interaction": None,
            "session_count": 0
        }
        
    def _save_context(self):
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save human context: {e}")
            
    def record_interaction(self, text: str):
        """Update context heuristically based on interaction."""
        self.context["last_interaction"] = datetime.now().isoformat()
        
        # Super lightweight semantic pattern recognition
        t = text.lower()
        if any(w in t for w in ["exhausted", "burnout", "tired", "stressed", "too much", "heavy"]):
            self.context["emotional_patterns"]["current_stress_level"] = "high"
        elif any(w in t for w in ["excited", "good", "great", "perfect", "love it"]):
            self.context["emotional_patterns"]["current_stress_level"] = "low"
        elif any(w in t for w in ["reset", "normal", "okay", "fine"]):
            self.context["emotional_patterns"]["current_stress_level"] = "balanced"
            
        self._save_context()
        
    def get_context_summary(self) -> str:
        """Export context for the LLM system prompt."""
        stress = self.context["emotional_patterns"].get("current_stress_level", "balanced")
        projects = self.context.get("active_projects", [])
        
        summary = f"HUMAN CONTEXT [STRESS: {stress.upper()}]"
        if projects:
            summary += f" | PROJECTS: {', '.join(projects)}"
            
        return summary

# Global singleton
human_context = HumanContextManager()
