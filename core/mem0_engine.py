"""
JARVIS Autonomous Intelligence 2.0 — Mem0 Persistent Intelligent Memory Engine
Provides long-term episodic, semantic, and preference recall across sessions using Mem0,
backed by embedded Qdrant vector storage and zero-quota FastEmbed embeddings.
"""
import os
import logging
from typing import Dict, Any, List, Optional
import config

logger = logging.getLogger("jarvis.mem0_engine")


class Mem0Engine:
    """
    Intelligent Persistent Memory Engine powered by Mem0.
    Stores and retrieves structured user preferences, habits, facts, and context graphs.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.path.join(getattr(config, "DATA_DIR", "data"), "mem0_qdrant")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.memory = None
        self._initialized = False
        self._init_mem0()

    def _init_mem0(self):
        """Initializes Mem0 with embedded Qdrant, FastEmbed local embeddings, and Gemini extraction."""
        try:
            from mem0 import Memory

            gemini_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
            groq_key = getattr(config, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")

            # 1. Primary: Google Gemini 3.5 Flash Lite (High RPM, dedicated quota)
            if gemini_key:
                os.environ["GEMINI_API_KEY"] = gemini_key
                mem0_config = {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "path": self.storage_dir,
                            "embedding_model_dims": 384
                        }
                    },
                    "embedder": {
                        "provider": "fastembed",
                        "config": {
                            "model": "BAAI/bge-small-en-v1.5"
                        }
                    },
                    "llm": {
                        "provider": "gemini",
                        "config": {
                            "model": "gemini-3.5-flash-lite",
                            "api_key": gemini_key
                        }
                    }
                }
            # 2. Secondary: Groq fallback
            elif groq_key:
                os.environ["GROQ_API_KEY"] = groq_key
                mem0_config = {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "path": self.storage_dir,
                            "embedding_model_dims": 384
                        }
                    },
                    "embedder": {
                        "provider": "fastembed",
                        "config": {
                            "model": "BAAI/bge-small-en-v1.5"
                        }
                    },
                    "llm": {
                        "provider": "groq",
                        "config": {
                            "model": "openai/gpt-oss-20b",
                            "api_key": groq_key
                        }
                    }
                }
            else:
                logger.warning("No API key available for Mem0 extraction. Mem0 operating in fallback mode.")
                return

            self.memory = Memory.from_config(mem0_config)
            self._initialized = True
            logger.info(f"Mem0 Persistent Memory Engine active. Storage: {self.storage_dir}")
        except Exception as e:
            logger.error(f"Mem0 initialization error: {e}")
            self.memory = None
            self._initialized = False

    def is_available(self) -> bool:
        """Returns True if Mem0 is initialized and operational."""
        return self._initialized and self.memory is not None

    def add_memory(self, content: str, user_id: str = "Ayush", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extracts semantic facts and saves them to user's persistent memory.
        """
        if not content or not content.strip():
            return {"status": "error", "error": "Empty content payload"}

        if not self.is_available():
            # Graceful fallback to OmegaMemory file store
            try:
                from core.omega_memory import OmegaMemory
                om = OmegaMemory()
                om.add_long_term_fact(content.strip())
                return {"status": "success", "engine": "omega_fallback", "content": content}
            except Exception as fe:
                return {"status": "error", "error": f"Mem0 offline and fallback failed: {fe}"}

        try:
            meta = metadata or {}
            res = self.memory.add(content.strip(), user_id=user_id, metadata=meta)
            logger.info(f"Mem0: Added memory for user '{user_id}': {res}")
            return {
                "status": "success",
                "engine": "mem0_qdrant",
                "results": res.get("results", []) if isinstance(res, dict) else res
            }
        except Exception as e:
            logger.error(f"Mem0 add_memory error: {e}")
            return {"status": "error", "error": str(e)}

    def search_memory(self, query: str, user_id: str = "Ayush", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Semantically queries persistent user memory for relevant facts or habits.
        """
        if not query or not query.strip():
            return []

        if not self.is_available():
            # Fallback to local regex/keyword matching in OmegaMemory
            try:
                from core.omega_memory import OmegaMemory
                om = OmegaMemory()
                return [{"memory": f, "engine": "omega_fallback"} for f in om.get_all_facts() if any(w in f.lower() for w in query.lower().split())]
            except Exception:
                return []

        try:
            filters = {"user_id": user_id}
            raw = self.memory.search(query.strip(), filters=filters, limit=limit)
            items = raw.get("results", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            # Multi-User Strict Isolation: Purge any cross-user memories
            isolated = []
            for r in items:
                r_user = r.get("user_id") or (r.get("metadata") or {}).get("user_id")
                if r_user is None or str(r_user) == str(user_id):
                    isolated.append(r)
                else:
                    logger.warning(f"[SECURITY] Blocked cross-user memory access: requested '{user_id}', item belongs to '{r_user}'")
            return isolated
        except Exception as e:
            logger.warning(f"Mem0 search error: {e}")
            return []

    def get_user_context(self, query: str, user_id: str = "Ayush", limit: int = 4) -> str:
        """
        Returns a formatted Markdown memory preamble suitable for injecting into LLM system prompts.
        """
        matches = self.search_memory(query, user_id=user_id, limit=limit)
        if not matches:
            return ""

        facts = []
        for m in matches:
            text = m.get("memory") or m.get("text")
            if text:
                facts.append(f"- {text}")

        if not facts:
            return ""

        context_block = "\n".join(facts)
        return f"\n### USER MEMORY & PREFERENCES (PERSISTENT RECALL):\n{context_block}\n"

    def get_all_memories(self, user_id: str = "Ayush") -> List[Dict[str, Any]]:
        """
        Fetches all memories recorded for the given user with strict isolation.
        """
        if not self.is_available():
            return []

        try:
            raw = self.memory.get_all(filters={"user_id": user_id})
            items = raw.get("results", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            isolated = []
            for r in items:
                r_user = r.get("user_id") or (r.get("metadata") or {}).get("user_id")
                if r_user is None or str(r_user) == str(user_id):
                    isolated.append(r)
            return isolated
        except Exception as e:
            logger.error(f"Mem0 get_all error: {e}")
            return []

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Removes a memory entry by ID.
        """
        if not self.is_available():
            return {"status": "error", "error": "Mem0 offline"}

        try:
            self.memory.delete(memory_id)
            return {"status": "success", "deleted_id": memory_id}
        except Exception as e:
            logger.error(f"Mem0 delete error: {e}")
            return {"status": "error", "error": str(e)}


# Global Singleton Instance
mem0_engine = Mem0Engine()
