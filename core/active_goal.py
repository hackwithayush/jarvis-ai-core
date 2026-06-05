"""
Persistent Goal Engine
Tracks long-running objectives, slot structures, and execution progress.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger("jarvis.goal")

class ActiveGoal:
    def __init__(self):
        self.goal_type: str = "idle"
        self.goal_status: str = "idle"  # idle, planning, executing, completed
        self.slots: Dict[str, Any] = {}
        self.progress: int = 0
        
    def set_goal(self, goal_type: str, required_slots: Dict[str, Any]):
        """Sets a new user objective and initial slot structures."""
        self.goal_type = goal_type
        self.goal_status = "planning"
        self.slots = required_slots
        self.progress = 0
        logger.info(f"[GOAL ENGINE] New goal activated: {goal_type}")
        
    def update_slot(self, key: str, value: Any):
        """Updates a specific slot value and recalculates progress."""
        if key in self.slots:
            self.slots[key] = value
            self.calculate_progress()
            logger.info(f"[GOAL ENGINE] Slot updated: {key} -> {value}")
            
    def get_missing_fields(self) -> List[str]:
        """Returns list of slots that are still missing (value is None)."""
        return [k for k, v in self.slots.items() if v is None]
        
    def calculate_progress(self):
        """Dynamic percentage calculations based on satisfied slots."""
        if not self.slots:
            self.progress = 0
            return
            
        total = len(self.slots)
        filled = sum(1 for v in self.slots.values() if v is not None)
        self.progress = int((filled / total) * 100)
        
        if self.progress == 100:
            self.goal_status = "executing"
            
    def is_ready_to_execute(self, user_message: str) -> bool:
        """Determines if the system should transition to MODE_EXECUTION."""
        if self.goal_type == "idle":
            return False
            
        # Explicit user execution trigger
        execute_triggers = ["make it", "execute", "go ahead", "build it", "start"]
        if any(trigger in user_message.lower() for trigger in execute_triggers):
            return True
            
        # Autonomous execution trigger if all primary slots are satisfied
        missing = self.get_missing_fields()
        if len(missing) == 0:
            return True
            
        return False
            
    def clear(self):
        """Reset the active goal system."""
        self.goal_type = "idle"
        self.goal_status = "idle"
        self.slots = {}
        self.progress = 0
        logger.info("[GOAL ENGINE] Goal successfully cleared.")

def extract_semantic_slots(message: str, model_manager, current_slots: dict) -> dict:
    """Uses LLM to extract structured entities and resolve conversational references."""
    import json
    prompt = f"""
You are a structured Entity Extractor.
Extract values for the following missing slots based on the user's message.
If the user says "use these two" or references previous context implicitly, infer the values logically.

Current Slots State:
{json.dumps(current_slots, indent=2)}

User Message:
{message}

Return ONLY a valid JSON dictionary mapping the slot keys to their newly extracted values. If a slot is not mentioned or cannot be inferred, do not include it. Do not use markdown blocks.
"""
    try:
        raw = model_manager.generate(messages=[{"role": "user", "content": prompt}], model="llama-3.1-70b-versatile")
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except Exception as e:
        logger.error(f"[SLOT EXTRACTOR ERROR] {e}")
        return {}

# Global Goal Instance
active_goal = ActiveGoal()
