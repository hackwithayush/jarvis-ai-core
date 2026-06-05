"""
JARVIS OMEGA — Enterprise Memory + Context Engine
Manages short-term session state and long-term selective memory persistence.
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class OmegaMemory:
    """Cognitive Memory Engine for JARVIS."""
    
    MEMORY_DB = os.path.join("data", "jarvis_memory.json")
    MAX_SHORT_MEMORY = 15
    MAX_LONG_MEMORY = 500
    IMPORTANCE_THRESHOLD = 7

    DEFAULT_MEMORY = {
        "profile": {
            "name": "Boss",
            "preferred_language": "english",
            "assistant_mode": "jarvis",
            "tone": "smart"
        },
        "session_memory": [],
        "long_term_memory": [],
        "conversation_summary": "",
        "system_state": {
            "last_active": "",
            "total_conversations": 0
        }
    }

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict:
        if not os.path.exists(self.MEMORY_DB):
            self._save_memory(self.DEFAULT_MEMORY)
            return self.DEFAULT_MEMORY
        try:
            with open(self.MEMORY_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Memory Corruption: {e}")
            return self.DEFAULT_MEMORY

    def _save_memory(self, memory: Dict):
        try:
            with open(self.MEMORY_DB, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=4)
        except Exception as e:
            logger.error(f"Memory Save Failure: {e}")

    def _generate_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _calculate_importance(self, text: str) -> int:
        score = 1
        important_keywords = [
            "remember", "my name", "project", "goal", "always", 
            "preference", "jarvis", "bug bounty", "anime", "language", "speak"
        ]
        text_lower = text.lower()
        for word in important_keywords:
            if word in text_lower:
                score += 3
        
        if len(text.split()) > 15:
            score += 2
        return score

    def _should_ignore(self, text: str) -> bool:
        ignore = ["hi", "hello", "hey", "yo", "okk", "ok", "hyy", "hmm"]
        return text.lower().strip() in ignore

    def update_session(self, role: str, content: str):
        """Update the short-term session buffer."""
        self.memory["session_memory"].append({
            "role": role,
            "content": content,
            "timestamp": str(datetime.now())
        })
        self.memory["session_memory"] = self.memory["session_memory"][-self.MAX_SHORT_MEMORY:]
        self._summarize()

    def update_long_term(self, user_input: str):
        """Process input for potential long-term persistence."""
        if self._should_ignore(user_input):
            return

        importance = self._calculate_importance(user_input)
        if importance < self.IMPORTANCE_THRESHOLD:
            return

        mem_id = self._generate_id(user_input)
        existing_ids = [m["id"] for m in self.memory["long_term_memory"]]
        
        if mem_id not in existing_ids:
            self.memory["long_term_memory"].append({
                "id": mem_id,
                "content": user_input,
                "importance": importance,
                "timestamp": str(datetime.now())
            })
            # Sort by importance and prune
            self.memory["long_term_memory"] = sorted(
                self.memory["long_term_memory"],
                key=lambda x: x["importance"],
                reverse=True
            )[:self.MAX_LONG_MEMORY]

            # --- Vector DB Persistence ---
            try:
                from core.knowledge_manager import KnowledgeManager
                km = KnowledgeManager()
                if km.enabled:
                    km.add_document(
                        content=user_input,
                        source="Omega Memory Engine",
                        title="Personal Fact",
                        category="personal"
                    )
                    logger.info(f"[VECTOR MEMORY] Saved fact: '{user_input}' to vector store.")
            except Exception as e:
                logger.error(f"[VECTOR MEMORY ERROR] Failed to save fact to vector store: {e}")

    def detect_preferences(self, user_input: str):
        """Dynamic profile adaptation based on conversation flow."""
        text = user_input.lower()
        
        # Language Sync
        languages = {"french": "french", "spanish": "spanish", "english": "english", "hindi": "hindi"}
        for lang in languages:
            if f"speak {lang}" in text:
                self.memory["profile"]["preferred_language"] = languages[lang]

        # Tactical Mode Sync
        if "anime mode" in text:
            self.memory["profile"]["assistant_mode"] = "anime"
        elif "bug bounty mode" in text or "security mode" in text:
            self.memory["profile"]["assistant_mode"] = "security"
        elif "normal mode" in text or "jarvis mode" in text:
            self.memory["profile"]["assistant_mode"] = "jarvis"

    def _summarize(self):
        """Build a tactical summary of the most recent exchange."""
        recent = self.memory["session_memory"][-5:]
        summary = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
        self.memory["conversation_summary"] = summary

    def build_context(self, query: str = "") -> str:
        """Synthesize the full system context prompt with semantic vector memory."""
        p = self.memory["profile"]
        long_memories = "\n".join([f"- {m['content']}" for m in self.memory["long_term_memory"][:5]])
        
        # Semantic Vector Memories (via ChromaDB RAG)
        vector_memories = ""
        if query:
            try:
                from core.knowledge_manager import KnowledgeManager
                km = KnowledgeManager()
                if km.enabled:
                    results = km.search(query, n_results=5)
                    # Filter results for personal category
                    personal_hits = [r for r in results if r.get("category") == "personal"]
                    if personal_hits:
                        vector_memories = "\n".join([f"- {r['content']}" for r in personal_hits])
            except Exception as e:
                logger.error(f"Failed to query vector memory: {e}")
        
        context_prompt = f"""
YOU ARE JARVIS OMEGA.

ACTIVE NEURAL PROFILE:
- User Identity: {p['name']}
- Language Grid: {p['preferred_language']}
- Tactical Mode: {p['assistant_mode']}
- Intelligence Tone: {p['tone']}

RELEVANT LONG-TERM MEMORIES:
{long_memories if long_memories else "No previous mission data recorded."}
"""
        if vector_memories:
            context_prompt += f"""
RELEVANT SEMANTIC MEMORIES (VECTOR STORE):
{vector_memories}
"""
        context_prompt += f"""
RECENT CONVERSATIONAL CONTEXT:
{self.memory['conversation_summary']}

CORE DIRECTIVES:
1. Maintain continuity with the profile and long-term memories provided.
2. ADAPTIVE BEHAVIOR: Never overanalyze typos or nonsensical text. If input is unclear, respond casually ("Didn't catch that, Boss") and ask briefly for clarification.
3. NO ROBOTIC NARRATION: Avoid phrases like "Communication disruption" or "System instability." Behave confidently.
4. TECHNICAL INTENT: Never explain obvious commands (python, pip, cd). Continue naturally.
5. CONCISENESS: Keep casual responses under 15 words. Enter deep analysis mode only for complex tasks (coding, security, research).
6. Never lecture the user or repeat previous messages unless asked.
"""
        return context_prompt

    def process_input(self, user_input: str) -> str:
        """Main pipeline: Load -> Process -> Save -> Return Context."""
        self.detect_preferences(user_input)
        self.update_session("user", user_input)
        self.update_long_term(user_input)
        
        self.memory["system_state"]["last_active"] = str(datetime.now())
        self.memory["system_state"]["total_conversations"] += 1
        
        self._save_memory(self.memory)
        return self.build_context(user_input)

