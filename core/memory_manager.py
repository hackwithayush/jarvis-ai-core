"""
Memory Manager — Adaptive User Personalization
Extracts and stores user preferences, style, and facts for long-term recall.
"""
import json
import logging
import re
from typing import Dict, Any, Optional
import config

logger = logging.getLogger(__name__)

class MemoryManager:
    """Handles extraction and management of user-specific memory patterns."""

    def __init__(self):
        # Common patterns to identify preferences/facts
        self.extraction_patterns = {
            "name": [r"my name is ([\w\s]+)", r"call me ([\w\s]+)"],
            "preference": [r"i prefer ([\w\s]+)", r"i like ([\w\s]+)", r"use ([\w\s]+) from now on"],
            "occupation": [r"i am a ([\w\s]+)", r"i work as a ([\w\s]+)"],
            "language": [r"i speak ([\w]+)", r"respond in ([\w]+)"]
        }
        self.knowledge = None # Injected late to avoid circular imports

    def extract_preferences(self, message: str, current_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Scan a user message for new preferences and merge with existing ones."""
        message = message.lower()
        new_prefs = current_prefs.copy()
        
        found_any = False
        for key, patterns in self.extraction_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message)
                if match:
                    value = match.group(1).strip()
                    logger.info(f"Memory Extract: Found {key} -> {value}")
                    new_prefs[key] = value
                    found_any = True
        
        return new_prefs if found_any else current_prefs

    def learn_permanent_facts(self, message: str, model_manager: Any, knowledge_manager: Any) -> bool:
        """Use Neural Audit to extract and save permanent facts to Vector DB."""
        # 1. Audit Message for Fact Potential
        neural_prompt = f"Audit the user message: '{message}'. Is there a permanent fact about the user (name, job, birthday, home, hobby)? If yes, extract it as a short fact string. If no, answer 'NONE'."
        fact = model_manager.generate(
            [{"role": "user", "content": neural_prompt}],
            system_prompt="You are a precise Memory Auditor. Extract ONLY the fact or say 'NONE'.",
            model=config.ROUTING_CONFIG.get("fast", "phi3:mini")
        )
        
        if fact and "NONE" not in fact.upper() and len(fact) > 5:
            logger.info(f"Neural Memory: Extracted fact -> {fact}")
            # 2. Sync to Vector DB
            knowledge_manager.add_document(
                content=fact,
                source="Neural Memory Engine",
                title="Personal Fact",
                category="personal"
            )
            return True
        return False

    def learn_interests(self, message: str, current_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Track user interest frequency based on message content."""
        message = message.lower()
        new_prefs = current_prefs.copy()
        interests = new_prefs.get("interests", {})
        
        # Simple keyword extraction (excluding common stop words)
        words = re.findall(r'\b\w{4,}\b', message) # Only words with length >= 4
        stop_words = {"this", "that", "with", "from", "your", "have", "they", "there", "what", "when", "where", "which"}
        
        for word in words:
            if word not in stop_words:
                interests[word] = interests.get(word, 0) + 1
        
        # Keep only top 20 interests to avoid bloating
        if len(interests) > 20:
            interests = dict(sorted(interests.items(), key=lambda x: x[1], reverse=True)[:20])
            
        new_prefs["interests"] = interests
        return new_prefs

    def detect_media_intent(self, message: str) -> str:
        """Classify if the message is about movies, anime, or k-dramas."""
        text = message.lower()
        if any(kw in text for kw in ["kdrama", "korean drama", "k-drama", "vincenzo", "glory"]):
            return "kdrama"
        if any(kw in text for kw in ["anime", "manga", "naruto", "jujutsu", "otaku"]):
            return "anime"
        if any(kw in text for kw in ["movie", "cinema", "film", "netflix", "watch"]):
            return "movie"
        return "general"

    def learn_taste(self, message: str, current_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Learn and store user entertainment tastes over time."""
        intent = self.detect_media_intent(message)
        if intent == "general":
            return current_prefs
            
        new_prefs = current_prefs.copy()
        taste = new_prefs.get("entertainment_taste", [])
        taste.append(intent)
        
        # Keep recent 20 tastes
        if len(taste) > 20:
            taste = taste[-20:]
            
        new_prefs["entertainment_taste"] = taste
        return new_prefs

    def predict_next(self, prefs: Dict[str, Any]) -> Optional[str]:
        """Identify the top user interest for proactive suggestions."""
        interests = prefs.get("interests", {})
        if not interests:
            return None
            
        # Select the highest frequency interest
        sorted_interests = sorted(interests.items(), key=lambda x: x[1], reverse=True)
        top_interest, count = sorted_interests[0]
        
        # Only suggest if we have some confidence (e.g., seen at least twice)
        return top_interest if count >= 2 else None

    def build_memory_snippet(self, prefs: Dict[str, Any]) -> str:
        """Construct a prompt segment based on stored user memory."""
        if not prefs:
            return ""
            
        snippet = "\n--- USER CONTEXT (Memory Engagement) ---\n"
        if "name" in prefs:
            snippet += f"User Identity: {prefs['name']}\n"
        if "preference" in prefs:
            snippet += f"Preferences: {prefs['preference']}\n"
        if "occupation" in prefs:
            snippet += f"User Role: {prefs['occupation']}\n"
            
        return snippet + "---------------------------------------\n"
