"""
Memory Priority Engine
Scores and categorizes memory to prevent bloat and maintain long-term context relevance.
"""
from enum import Enum
import time

class MemoryTier(Enum):
    TEMPORARY = 1    # Expires quickly (e.g., Turn on the lights)
    PERSISTENT = 2   # Lasts for the session/project
    CRITICAL = 3     # Never expires (e.g., User preferences, IDs)

class PriorityEngine:
    def __init__(self):
        self.memory_store = []
        print("[MEMORY] Priority Engine Initialized.")
        
    def store_memory(self, content: str, tier: MemoryTier = MemoryTier.TEMPORARY):
        """ Stores memory with an expiration timestamp based on its tier. """
        expiration = None
        if tier == MemoryTier.TEMPORARY:
            expiration = time.time() + 3600 # 1 hour
        elif tier == MemoryTier.PERSISTENT:
            expiration = time.time() + 604800 # 1 week
            
        entry = {
            "content": content,
            "tier": tier.name,
            "timestamp": time.time(),
            "expires": expiration
        }
        self.memory_store.append(entry)
        print(f"[MEMORY] Stored {tier.name} context: {content[:50]}...")
        
    def cleanup_bloat(self):
        """ Removes expired temporary memories to save RAM. """
        current_time = time.time()
        initial_count = len(self.memory_store)
        self.memory_store = [m for m in self.memory_store if m["expires"] is None or m["expires"] > current_time]
        removed = initial_count - len(self.memory_store)
        if removed > 0:
            print(f"[MEMORY] Cleaned up {removed} expired memory nodes.")
