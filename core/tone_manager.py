"""
Dialogue Tone Manager
Dynamically alters Jarvis's response tone based on real-time cognitive metrics.
Tones: Decisive, Exploratory, Urgent, Balanced.
"""
from typing import Dict, Any

class ToneManager:
    @staticmethod
    def get_tone_directive(metrics: Dict[str, float]) -> str:
        """Determines conversational style modifiers based on cognitive metrics."""
        confidence = metrics.get("confidence", 0.5)
        stress = metrics.get("stress", 0.0)
        curiosity = metrics.get("curiosity", 0.5)
        fatigue = metrics.get("fatigue", 0.0)
        
        # Priority mapping of conversational rules
        if stress > 0.6:
            return "TONE DIRECTIVE: System stress is high. Speak curtly, urgently, and deliver maximum technical density with zero fluff or pleasantries."
        elif fatigue > 0.75:
            return "TONE DIRECTIVE: High fatigue detected. Keep your sentences short, simple, and direct. Defer complex tasks where appropriate."
        elif confidence > 0.8:
            return "TONE DIRECTIVE: Absolute confidence online. Speak decisively, authoritatively, and with flawless execution styling."
        elif curiosity > 0.7:
            return "TONE DIRECTIVE: High curiosity state. Probe the user with structural, clarifying questions and seek edge-case alternatives."
            
        return "TONE DIRECTIVE: Standard balanced operating mode. Speak naturally, supportively, and as a highly intelligent holographic companion."
