"""
JARVIS AI - Neural Router
Analyzes user input and determines the optimal execution pathway and model.
"""

import re
from typing import Dict, Any

class NeuralRouter:
    def __init__(self):
        # Models mapped directly to the optimized JARVIS hardware stack
        self.MODELS = {
            "coding": "qwen2.5-coder:7b",
            "reasoning": "deepseek-r1:7b",
            "chat": "llama3.1:8b",
            "heavy_intelligence": "llama-3.3-70b-versatile",
            "vision": "llama-3.2-11b-vision-preview", 
            "memory": "all-MiniLM-L6-v2"
        }
        
    def analyze_intent(self, user_input: str, has_image: bool = False, force_heavy: bool = False) -> Dict[str, Any]:
        """
        Determines the appropriate routing path for a given input.
        """
        prompt = user_input.lower()
        
        # 1. Vision Route (Screenshot/Image)
        if has_image or any(kw in prompt for kw in ["look at", "see this", "image", "screenshot", "what's in this", "picture"]):
            return {
                "route_type": "vision",
                "model": self.MODELS["vision"],
                "strategy": "Vision Model: Analyze image and provide visual context."
            }
            
        # 2. Heavy Intelligence Route (Cloud 70B)
        if force_heavy or any(kw in prompt for kw in ["comprehensive", "deep dive", "heavy analysis", "complex architecture"]):
            return {
                "route_type": "heavy_intelligence",
                "model": self.MODELS["heavy_intelligence"],
                "strategy": "Cloud 70B: Use heavy intelligence for maximum cognitive capability."
            }
            
        # 3. Coding Task Route (Qwen2.5-Coder)
        if any(kw in prompt for kw in ["code", "script", "python", "debug", "fix error", "programming", "terminal", "algorithm"]):
            return {
                "route_type": "coding",
                "model": self.MODELS["coding"],
                "strategy": "Qwen2.5-Coder 7B: Execute specialized syntax and logical formulation."
            }
            
        # 4. Memory Search Route (MiniLM + ChromaDB)
        if any(kw in prompt for kw in ["remember", "recall", "did i", "past", "history", "search memory", "earlier"]):
            return {
                "route_type": "memory",
                "model": self.MODELS["memory"],
                "strategy": "MiniLM + ChromaDB: Generate embeddings and query vector store."
            }
            
        # 5. Complex Reasoning Route (DeepSeek R1)
        if any(kw in prompt for kw in ["why", "explain", "logic", "how does", "reasoning", "think", "solve", "math", "theory"]):
            return {
                "route_type": "reasoning",
                "model": self.MODELS["reasoning"],
                "strategy": "DeepSeek R1 7B: Execute chain-of-thought logic and deep reasoning."
            }
            
        # 6. Default General Chat Route (Llama 3.1)
        return {
            "route_type": "general_chat",
            "model": self.MODELS["chat"],
            "strategy": "Llama3.1 8B: Execute fast conversational interaction."
        }
