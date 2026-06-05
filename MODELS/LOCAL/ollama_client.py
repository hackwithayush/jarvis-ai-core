"""
Ollama Local Client
Interfaces with the local Ollama daemon for inference.
"""

import requests
import json
import sys
import os

from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

OLLAMA_HOST = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

class OllamaClient:
    def __init__(self):
        self.host = OLLAMA_HOST
        
    def generate(self, prompt: str, model: str) -> str:
        """
        Sends a request to local Ollama.
        """
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except Exception as e:
            print(f"[MODEL ERROR] {model} failed: {e}. Falling back to deepseek-r1:7b...")
            fallback_model = "deepseek-r1:7b"
            
            # Prevent infinite fallback loop if deepseek-r1:7b itself is failing
            if model == fallback_model:
                return f"[Critical Error] Primary model '{model}' failed and it is the fallback: {e}"
                
            fallback_payload = {
                "model": fallback_model,
                "prompt": prompt,
                "stream": False
            }
            
            try:
                fb_response = requests.post(url, json=fallback_payload, timeout=120)
                fb_response.raise_for_status()
                return fb_response.json().get("response", "").strip()
            except Exception as fb_e:
                return f"[Critical Error] Fallback model also failed: {fb_e}"

if __name__ == "__main__":
    client = OllamaClient()
    # Test fallback by requesting a non-existent model
    print("Testing Fallback Logic:", client.generate("Are you online?", "fake_model:latest"))
