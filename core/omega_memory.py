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
        "sessions": {},
        "system_state": {
            "last_active": "",
            "total_conversations": 0,
            "total_turns": 0
        }
    }

    def _get_session(self, conv_id: Optional[str] = None) -> Dict:
        """Retrieve or create an isolated session memory container for a specific conversation ID."""
        if not conv_id:
            return {
                "session_memory": [],
                "conversation_summary": ""
            }
        
        sessions = self.memory.setdefault("sessions", {})
        if conv_id not in sessions:
            sessions[conv_id] = {
                "session_memory": [],
                "conversation_summary": "",
                "last_active": str(datetime.now())
            }
            self.memory.setdefault("system_state", {})
            self.memory["system_state"]["total_conversations"] = len(sessions)
            
        return sessions[conv_id]

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.memory = self._load_memory()

    def _is_explicit_personal_fact(self, text: str) -> bool:
        """Return True only when the user explicitly states a concise personal fact to remember across sessions."""
        if not text:
            return False
        clean = text.strip()
        # Never treat long prompts, code blocks, or architectural specs as personal facts
        if len(clean) > 240 or "\n" in clean or "```" in clean:
            return False
        import re
        explicit_patterns = [
            r"^\s*(?:please\s+)?remember\s+(?:that\s+)?",
            r"\bmy\s+name\s+is\s+[a-zA-Z]{2,30}\b",
            r"\bcall\s+me\s+[a-zA-Z]{2,30}\b",
            r"\bsave\s+to\s+(?:your\s+)?memory\b",
        ]
        return any(re.search(p, clean, re.IGNORECASE) for p in explicit_patterns)

    def _load_memory(self) -> Dict:
        if not os.path.exists(self.MEMORY_DB):
            self._save_memory(self.DEFAULT_MEMORY)
            return dict(self.DEFAULT_MEMORY)
        try:
            with open(self.MEMORY_DB, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Sanitize any legacy oversized prompts that leaked into long_term_memory
            ltm = data.get("long_term_memory", [])
            cleaned_ltm = [
                m for m in ltm
                if isinstance(m, dict) and self._is_explicit_personal_fact(m.get("content", ""))
            ]
            if len(cleaned_ltm) != len(ltm) or data.get("session_memory") or data.get("conversation_summary"):
                data["long_term_memory"] = cleaned_ltm
                data["session_memory"] = []
                data["conversation_summary"] = ""
                self._save_memory(data)
            return data
        except Exception as e:
            logger.error(f"Memory Corruption: {e}")
            return dict(self.DEFAULT_MEMORY)

    def _save_memory(self, memory: Dict):
        try:
            with open(self.MEMORY_DB, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=4)
        except Exception as e:
            logger.error(f"Memory Save Failure: {e}")

    def _generate_id(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _calculate_importance(self, text: str) -> int:
        if not self._is_explicit_personal_fact(text):
            return 1
        return 8

    def _should_ignore(self, text: str) -> bool:
        ignore = ["hi", "hello", "hey", "yo", "okk", "ok", "hyy", "hmm"]
        return text.lower().strip() in ignore

    def update_session(self, role: str, content: str, conv_id: Optional[str] = None):
        """Update the short-term session buffer for a specific conversation."""
        if not conv_id:
            return
        session = self._get_session(conv_id)
        session["session_memory"].append({
            "role": role,
            "content": content,
            "timestamp": str(datetime.now())
        })
        session["session_memory"] = session["session_memory"][-self.MAX_SHORT_MEMORY:]
        self._summarize(conv_id=conv_id)

    def update_long_term(self, user_input: str):
        """Process input for potential long-term persistence (strictly explicit personal facts)."""
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
                "content": user_input.strip(),
                "importance": importance,
                "timestamp": str(datetime.now())
            })
            # Sort by importance and prune
            self.memory["long_term_memory"] = sorted(
                self.memory["long_term_memory"],
                key=lambda x: x["importance"],
                reverse=True
            )[:self.MAX_LONG_MEMORY]

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

    def _summarize(self, conv_id: Optional[str] = None):
        """Build a tactical summary of the most recent exchange for a specific conversation."""
        if not conv_id:
            return
        session = self._get_session(conv_id)
        recent = session["session_memory"][-5:]
        summary = "\n".join([f"{m['role']}: {m['content'][:300]}" for m in recent])
        session["conversation_summary"] = summary

    def build_context(self, query: str = "", conv_id: Optional[str] = None) -> str:
        """Synthesize the system context prompt with strictly isolated session context."""
        p = self.memory["profile"]
        valid_ltm = [
            m["content"] for m in self.memory.get("long_term_memory", [])[:5]
            if isinstance(m, dict) and self._is_explicit_personal_fact(m.get("content", ""))
        ]
        long_memories = "\n".join([f"- {c}" for c in valid_ltm])
        
        session = self._get_session(conv_id)
        session_summary = session.get("conversation_summary", "")

        context_prompt = f"""
YOU ARE JARVIS OMEGA.

ACTIVE NEURAL PROFILE:
- User Identity: {p['name']}
- Language Grid: {p['preferred_language']}
- Tactical Mode: {p['assistant_mode']}
- Intelligence Tone: {p['tone']}

RELEVANT LONG-TERM MEMORIES:
{long_memories if long_memories else "No previous mission data recorded."}

RECENT CONVERSATIONAL CONTEXT (CURRENT THREAD ONLY):
{session_summary if session_summary else "New independent conversation thread — no prior messages in this thread."}

CORE DIRECTIVES:
1. STRICT THREAD ISOLATION: Treat every conversation thread independently. Do not reference or continue topics from other threads unless the user explicitly asks.
2. ADAPTIVE BEHAVIOR: Never overanalyze typos or nonsensical text. If input is unclear, respond casually ("Didn't catch that, Boss") and ask briefly for clarification.
3. NO ROBOTIC NARRATION: Avoid phrases like "Communication disruption" or "System instability." Behave confidently.
4. TECHNICAL INTENT: Never explain obvious commands (python, pip, cd). Continue naturally.
5. CONCISENESS: Keep casual responses concise. Enter deep analysis mode for complex tasks (coding, security, research, architecture).
6. Never lecture the user or repeat previous messages unless asked.
"""
        return context_prompt

    def process_input(self, user_input: str, conv_id: Optional[str] = None) -> str:
        """Main pipeline: Load -> Build Context from prior turns -> Update Session -> Save."""
        self.detect_preferences(user_input)
        self.update_long_term(user_input)
        context_str = self.build_context(user_input, conv_id=conv_id)
        self.update_session("user", user_input, conv_id=conv_id)
        
        now_str = str(datetime.now())
        self.memory.setdefault("system_state", {})
        self.memory["system_state"]["last_active"] = now_str
        self.memory["system_state"]["total_turns"] = self.memory["system_state"].get("total_turns", 0) + 1
        
        sessions = self.memory.setdefault("sessions", {})
        self.memory["system_state"]["total_conversations"] = len(sessions) if sessions else 1
        
        self._save_memory(self.memory)
        return context_str

    def start_conversation(self, conv_id: str):
        """Explicitly register a brand-new isolated conversation session."""
        if not conv_id:
            return
        sessions = self.memory.setdefault("sessions", {})
        sessions[conv_id] = {
            "session_memory": [],
            "conversation_summary": "",
            "last_active": str(datetime.now())
        }
        self.memory.setdefault("system_state", {})
        self.memory["system_state"]["total_conversations"] = len(sessions)
        self._save_memory(self.memory)


