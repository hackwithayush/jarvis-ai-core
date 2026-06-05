"""
Jarvis v15.0 — Hierarchical Context & Memory Engine (L1/L2/L3 Memory)
Provides robust token budgeting, sliding summarization, local SQLite-backed semantic keyword retrieval,
and proactive background summarization.
"""
import os
import sqlite3
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("jarvis.context_engine")

class HierarchicalMemoryManager:
    """Three-tiered memory architecture (L1 Working Attention, L2 Summary Buffer, L3 SQLite Retrieval)."""

    def __init__(self, db_path: str = None, token_budget_chars: int = 12000):
        if not db_path:
            # Default directory inside workspace
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(cwd, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "neural_retrieval.db")
            
        self.db_path = db_path
        self.token_budget_chars = token_budget_chars
        self._init_db()

    def _init_db(self):
        """Initializes the L3 SQLite retrieval memory and summary profile tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    query TEXT,
                    response TEXT,
                    tags TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summary_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_updated TEXT,
                    summary TEXT,
                    key_facts TEXT,
                    user_preferences TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"L3 SQLite Retrieval & Summary Profile DB initialized at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize L3 database: {e}")

    def archive_interaction(self, query: str, response: str, tags: str = "general"):
        """Stores a conversation exchange into L3 SQLite long-term storage."""
        if not query.strip() or not response.strip():
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO semantic_memory (timestamp, query, response, tags) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), query.strip(), response.strip(), tags)
            )
            conn.commit()
            conn.close()
            logger.debug(f"[L3 ARCHIVE] Saved interaction: {query[:30]}...")
        except Exception as e:
            logger.error(f"Failed to archive interaction in L3: {e}")

    def semantic_retrieve(self, current_query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves the top N historical exchanges matching the query.
        Uses a lightweight TF-IDF keyword overlap metric computed locally in SQL and Python.
        """
        if not current_query.strip():
            return []
            
        # Extract alphanumeric keywords (stop words ignored)
        stop_words = {"the", "a", "an", "and", "or", "but", "if", "then", "of", "to", "in", "on", "for", "with", "is", "was", "how", "what", "why"}
        words = re.findall(r"\w+", current_query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        if not keywords:
            # Fallback to standard word match
            keywords = [w for w in words if len(w) > 1]
            
        if not keywords:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Fetch all memories to perform scoring
            cursor.execute("SELECT query, response, timestamp, tags FROM semantic_memory")
            rows = cursor.fetchall()
            conn.close()
            
            scored_memories = []
            for row in rows:
                hist_query, response, timestamp, tags = row
                hist_lower = hist_query.lower()
                
                # Calculate simple token overlap score
                score = 0
                for kw in keywords:
                    if kw in hist_lower:
                        score += 1.0
                        
                if score > 0:
                    scored_memories.append({
                        "query": hist_query,
                        "response": response,
                        "timestamp": timestamp,
                        "tags": tags,
                        "score": score
                    })
                    
            # Sort by score descending, then timestamp descending
            scored_memories.sort(key=lambda x: (x["score"], x["timestamp"]), reverse=True)
            return scored_memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve semantic memories: {e}")
            return []

    def get_summary_profile(self) -> Dict[str, str]:
        """Retrieves the persistent summary profile from L3 SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT summary, key_facts, user_preferences FROM summary_profile ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "summary": row[0] or "",
                    "key_facts": row[1] or "",
                    "user_preferences": row[2] or ""
                }
        except Exception as e:
            logger.error(f"Failed to fetch summary profile: {e}")
        return {"summary": "", "key_facts": "", "user_preferences": ""}

    def save_summary_profile(self, summary: str, key_facts: str, user_preferences: str):
        """Saves or updates the persistent summary profile in SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO summary_profile (last_updated, summary, key_facts, user_preferences) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), summary, key_facts, user_preferences)
            )
            conn.commit()
            conn.close()
            logger.info("[L3 SUMMARY] Proactive context summary profile updated.")
        except Exception as e:
            logger.error(f"Failed to save summary profile: {e}")

    def generate_proactive_summary(self, messages: List[Dict[str, str]]):
        """
        Asynchronously runs an LLM summarization process over conversation history.
        Extracts high-level summary, key facts, and persistent user preferences.
        """
        if len(messages) < 2:
            return
            
        try:
            from core.model_manager import ModelManager
            model_mgr = ModelManager()
            
            # Combine history for context
            history_text = "\n".join([f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages])
            
            current_profile = self.get_summary_profile()
            
            prompt = f"""
You are the JARVIS Memory Summarization Subsystem.
Analyze the following conversation history and synthesize/update the persistent memory profile.

=== CURRENT SUMMARY PROFILE ===
Summary: {current_profile['summary']}
Key Facts: {current_profile['key_facts']}
User Preferences: {current_profile['user_preferences']}

=== NEW CONVERSATION TURNS ===
{history_text}

=== INSTRUCTIONS ===
Update the memory profile by blending the current state with the new turns. Extract:
1. A concise historical summary of active objectives and dialogue.
2. A list of key facts (e.g. environment specifics, active variables).
3. User preferences (e.g. coding styling, tools preferred).

Return ONLY a valid JSON dictionary mapping keys "summary", "key_facts", and "user_preferences" (as strings or lists) to their updated values. Do not use markdown blocks or comments.
"""
            # Use cheap fast reasoning model or default routing
            raw_response = model_mgr.generate(messages=[{"role": "user", "content": prompt}], model="llama-3.1-8b-instant")
            
            # Parse JSON safely
            clean = raw_response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)
            
            summary = parsed.get("summary", "")
            key_facts = parsed.get("key_facts", "")
            if isinstance(key_facts, list):
                key_facts = "\n".join(f"- {f}" for f in key_facts)
            user_pref = parsed.get("user_preferences", "")
            if isinstance(user_pref, list):
                user_pref = "\n".join(f"- {p}" for p in user_pref)
                
            self.save_summary_profile(summary, key_facts, user_pref)
            
            # Publish memory summarized event via EventBus if available
            try:
                from core.event_bus import event_bus
                event_bus.publish("memory/summarized", {
                    "summary": summary,
                    "key_facts": key_facts,
                    "user_preferences": user_pref
                })
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"[MEMORY SUMMARIZER ERROR] Asynchronous proactive summary failed: {e}")

    def manage_context(self, messages: List[Dict[str, str]], system_prompt: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Token budgeting coordinator.
        - L1 Active Attention: Retains the last 4 messages at 100% resolution.
        - L2 Summarizer: Compresses messages 5+ into a consolidated history recap.
        """
        if not messages:
            return [], {}

        l1_messages = []
        l2_messages_to_summarize = []
        
        # Retain last 4 turns for L1 Working Attention
        l1_count = min(4, len(messages))
        if l1_count > 0:
            l1_messages = messages[-l1_count:]
            l2_messages_to_summarize = messages[:-l1_count]
        else:
            l1_messages = messages
            
        summary_payload = ""
        
        # Retrieve and blend persistent summary profile
        profile = self.get_summary_profile()
        if profile["summary"] or profile["key_facts"] or profile["user_preferences"]:
            profile_lines = []
            if profile["summary"]:
                profile_lines.append(f"Summary: {profile['summary']}")
            if profile["key_facts"]:
                profile_lines.append(f"Key Facts:\n{profile['key_facts']}")
            if profile["user_preferences"]:
                profile_lines.append(f"User Preferences:\n{profile['user_preferences']}")
            summary_payload = "\n".join(profile_lines)
            
        # Trigger async summarization in a separate thread if l2 backlog accumulates
        if len(l2_messages_to_summarize) >= 2:
            import threading
            threading.Thread(
                target=self.generate_proactive_summary,
                args=(l2_messages_to_summarize,),
                daemon=True
            ).start()
            
        # Build optimized context state
        context_metadata = {
            "l1_turns_count": len(l1_messages),
            "l2_summarized_count": len(l2_messages_to_summarize),
            "has_l2_summary": bool(summary_payload)
        }
        
        # Return modified history array and metadata
        processed_history = []
        if summary_payload:
            # Inline compressed contextual brief
            compressed_brief = (
                f"[SYSTEM HISTORICAL CONTEXT BRIEF]\n"
                f"The following is a condensed, proactive summary of previous conversation history turns:\n"
                f"\"\"\"\n{summary_payload[:4000]}\n\"\"\"\n"
                f"Reference this data only when relevant to the new user request below."
            )
            processed_history.append({"role": "system", "content": compressed_brief})
            
        processed_history.extend(l1_messages)
        return processed_history, context_metadata

# Global memory instance
memory_manager = HierarchicalMemoryManager()

# Multi-User Isolated Memory Cache
import hashlib
_user_memory_managers = {}

def get_memory_manager_for_user(username: str) -> HierarchicalMemoryManager:
    """
    Dynamically routes SQLite database paths per user/tenant:
    data/tenants/<tenant_hash>/neural_retrieval.db
    """
    if not username:
        return memory_manager
    
    username_str = str(username).strip()
    if not username_str:
        return memory_manager
        
    if username_str in _user_memory_managers:
        return _user_memory_managers[username_str]
        
    try:
        # Compute dynamic tenant hash
        tenant_hash = hashlib.sha256(username_str.encode("utf-8")).hexdigest()
        
        cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tenant_dir = os.path.join(cwd, "data", "tenants", tenant_hash)
        os.makedirs(tenant_dir, exist_ok=True)
        db_path = os.path.join(tenant_dir, "neural_retrieval.db")
        
        # Instantiate tenant-specific memory manager
        mgr = HierarchicalMemoryManager(db_path=db_path)
        _user_memory_managers[username_str] = mgr
        logger.info(f"Isolated memory engine mapped for tenant '{username_str}' at hash {tenant_hash[:8]}...")
        return mgr
    except Exception as e:
        logger.error(f"Failed to route isolated memory manager for '{username_str}', falling back to global: {e}")
        return memory_manager

