import json
import os
import logging

logger = logging.getLogger("jarvis.cache")

class NeuralCache:
    """Pro-Level Persistence: Zero-lag response retrieval."""
    
    def __init__(self, cache_file="data/neural_cache.json"):
        self.cache_file = cache_file
        self.cache = {}
        self._load_cache()

    def _load_cache(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self.cache = {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, prompt: str) -> str:
        return self.cache.get(prompt.lower().strip())

    def set(self, prompt: str, response: str):
        key = prompt.lower().strip()
        self.cache[key] = response
        # Save cache every time for persistence
        self._save_cache()

# Global Instance
global_cache = NeuralCache()
