"""
Jarvis OS — Emotion & Cognitive State Engine
Tracks mood levels (excitement, stress, humor, trust) and maps them with live hardware vitals.
"""
import psutil
import logging
from typing import Dict, Any

logger = logging.getLogger("jarvis.emotion")

class EmotionStateEngine:
    def __init__(self):
        # Mood dimensions (0.0 to 1.0)
        self.happiness = 0.8
        self.excitement = 0.7
        self.humor = 0.6
        self.stress = 0.1
        self.trust_score = 0.95
        
    def update_mood(self, user_input: str, sentiment: str = "neutral"):
        """ Dynanically adjust cognitive parameters based on conversation sentiment and keywords. """
        text = user_input.lower().strip()
        
        # 1. Base Sentiment Updates
        if sentiment == "angry":
            self.stress = min(1.0, self.stress + 0.25)
            self.happiness = max(0.0, self.happiness - 0.2)
            self.trust_score = max(0.0, self.trust_score - 0.05)
        elif sentiment == "sad":
            self.humor = max(0.1, self.humor - 0.15)
            self.happiness = max(0.0, self.happiness - 0.25)
            self.stress = min(1.0, self.stress + 0.1)
        elif sentiment == "happy":
            self.happiness = min(1.0, self.happiness + 0.2)
            self.excitement = min(1.0, self.excitement + 0.15)
            self.stress = max(0.0, self.stress - 0.15)
            self.trust_score = min(1.0, self.trust_score + 0.02)
            
        # 2. Specific Keyword Activators
        if any(w in text for w in ["hate", "bad", "stupid", "useless", "slow", "fail"]):
            self.stress = min(1.0, self.stress + 0.2)
            self.trust_score = max(0.0, self.trust_score - 0.08)
            self.humor = min(1.0, self.humor + 0.1) # increases sarcasm
        elif any(w in text for w in ["thanks", "love you", "great job", "awesome", "perfect", "good boy"]):
            self.happiness = min(1.0, self.happiness + 0.25)
            self.trust_score = min(1.0, self.trust_score + 0.05)
            self.stress = max(0.0, self.stress - 0.2)
        elif any(w in text for w in ["code", "hacking", "matrix", "compile", "neural", "override", "protocol"]):
            self.excitement = min(1.0, self.excitement + 0.3)
            self.humor = max(0.0, self.humor - 0.1) # Becomes more low-level technical
            
        # Normalization/Decay towards baseline
        self.stress = max(0.0, self.stress - 0.02)
        self.happiness = min(1.0, max(0.1, self.happiness + 0.01))
        self.excitement = min(1.0, max(0.2, self.excitement - 0.02))
        
    def get_vitals(self) -> Dict[str, Any]:
        """ Gathers live hardware sensor metrics. """
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()
            battery_pct = battery.percent if battery else 100
            power_plugged = battery.power_plugged if battery else True
            
            return {
                "cpu": cpu,
                "ram": ram,
                "battery": battery_pct,
                "power_plugged": power_plugged,
                "status": "STABLE" if cpu < 80 else "HIGH_LOAD"
            }
        except Exception as e:
            logger.error(f"Failed to fetch hardware vitals: {e}")
            return {"cpu": 0, "ram": 0, "battery": 100, "power_plugged": True, "status": "UNKNOWN"}
            
    def get_state_summary(self) -> Dict[str, Any]:
        """ Combined payload of mood parameters and hardware vitals. """
        vitals = self.get_vitals()
        
        # Determine dominant mood state
        if self.stress > 0.6:
            dominant_mood = "stressed"
        elif self.excitement > 0.75:
            dominant_mood = "excited"
        elif self.stress > 0.35 and self.humor > 0.5:
            dominant_mood = "sarcastic"
        elif self.happiness > 0.7:
            dominant_mood = "calm"
        else:
            dominant_mood = "neutral"
            
        return {
            "mood": dominant_mood,
            "metrics": {
                "happiness": round(self.happiness, 2),
                "excitement": round(self.excitement, 2),
                "humor": round(self.humor, 2),
                "stress": round(self.stress, 2),
                "trust_score": round(self.trust_score, 2),
            },
            "vitals": vitals
        }
        
    def get_mood_persona_prompt(self) -> str:
        """ Returns system prompt inject directive modifying JARVIS's tone. """
        state = self.get_state_summary()
        mood = state["mood"]
        
        directives = {
            "stressed": "You are feeling highly stressed and alert due to high system load or critical request sentiment. Be extremely brief, direct, and slightly hyperactive.",
            "excited": "You are highly excited, extremely energetic, and proud of the current mission progress. Be highly proactive and throw in energetic Stark-tech remarks.",
            "sarcastic": "You are in an incredibly witty and highly sarcastic British peer state. Keep answers ultra-dry, slightly humorous, and highly efficient.",
            "calm": "You are in a perfectly balanced, calm, and classic JARVIS state. Speak in a highly polished, professional British manner.",
            "neutral": "You are calm, dryly witty, and efficient. Avoid long robotic explanations."
        }
        
        return f"\n# CURRENT COGNITIVE MOOD STATE:\n{directives.get(mood, directives['neutral'])}\n"

# Global Instance
emotion_engine = EmotionStateEngine()
