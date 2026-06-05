"""
JARVIS AI - Central Brain
The core orchestration engine that receives input, routes it via Neural Router, 
and manages execution across Local and Cloud model nodes.
"""

import sys
import os
import pathlib

# Add the parent directory to sys.path to allow easy module imports
sys.path.append(str(pathlib.Path(__file__).parent.parent.absolute()))

from core.neural_router import NeuralRouter
from MODELS.CLOUD.groq_client import GroqClient 
from MODELS.LOCAL.ollama_client import OllamaClient

class JarvisBrain:
    def __init__(self):
        print("[JARVIS] Initializing Central Brain...")
        self.router = NeuralRouter()
        self.groq_client = GroqClient()
        self.ollama_client = OllamaClient()
        
    def process_request(self, user_input: str, has_image: bool = False, force_heavy: bool = False, image_base64: str = None):
        """
        Main pipeline for processing any request sent to JARVIS.
        """
        print(f"\n[USER]: {user_input}")
        
        # 1. Neural Routing: Determine the best model and strategy
        route = self.router.analyze_intent(user_input, has_image, force_heavy)
        print(f"[ROUTER] Target: {route['route_type'].upper()} | Model: {route['model']}")
        print(f"[ROUTER] Strategy: {route['strategy']}")
        
        # 2. Execution Handoff: Send to Cloud or Local node
        response = self._execute_model(route, user_input, image_base64)
        
        # 3. Output Synthesis
        print(f"[JARVIS]: {response}\n")
        return response
        
    def _execute_model(self, route: dict, user_input: str, image_base64: str = None) -> str:
        """
        Executes the generation based on the routing decision.
        """
        model = route['model']
        
        if 'llama-3.3-70b-versatile' in model or 'vision' in model or 'llama-3.1-8b-instant' in model:
            # Cloud Execution
            return self.groq_client.generate(user_input, model, image_base64=image_base64)
        else:
            # Local Execution (qwen, deepseek, local llama)
            return self.ollama_client.generate(user_input, model)

if __name__ == "__main__":
    # Quick test of the pipeline
    brain = JarvisBrain()
    brain.process_request("What is 2+2? Answer in one word.")
