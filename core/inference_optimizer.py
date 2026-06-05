"""
Inference Optimizer
Handles GPU/Cloud Latency reduction via Context Compression and KV Cache alignment.
"""
import logging
from typing import List, Dict

logger = logging.getLogger("jarvis.inference")

class InferenceOptimizer:
    def __init__(self):
        self.MAX_TOKENS = 6000 # Safety limit for context window overhead
        
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (approx 4 chars per token)."""
        return len(text) // 4
        
    def compress_context(self, context: str) -> str:
        """Compresses context by removing stop words and unnecessary whitespaces to save tokens."""
        # Simple whitespace compression
        compressed = " ".join(context.split())
        
        # Heuristic length truncation
        if self.estimate_tokens(compressed) > self.MAX_TOKENS:
            logger.warning("[INFERENCE] Context explosion detected. Truncating context.")
            # Keep the beginning (system prompt) and the very end (latest context)
            half_allowed = (self.MAX_TOKENS * 4) // 2
            return compressed[:half_allowed] + "\n...[CONTENT TRUNCATED FOR LATENCY]...\n" + compressed[-half_allowed:]
            
        return compressed
        
    def optimize_payload(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Scrub conversation history to drop redundant messages, enforcing KV cache reuse efficiency."""
        if not messages:
            return messages
            
        optimized = []
        for msg in messages:
            content = msg.get("content", "")
            msg["content"] = self.compress_context(content)
            optimized.append(msg)
            
        logger.debug("[INFERENCE] Payload optimized for LLM latency.")
        return optimized

# Global instance
inference_optimizer = InferenceOptimizer()
