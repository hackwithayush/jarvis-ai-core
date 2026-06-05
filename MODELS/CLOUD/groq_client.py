"""
Groq API Client
Interfaces with the Groq Cloud for fast LLaMA 70B and Vision reasoning.
"""

import os
import sys
import requests

from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

class GroqClient:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        if not self.api_key:
            print("[WARNING] GROQ_API_KEY is not set in environment or config!")
            
    def generate(self, prompt: str, model: str, image_base64: str = None) -> str:
        """
        Sends a request to Groq via standard REST API, supporting vision.
        """
        if not self.api_key:
            return "[Groq Error] API Key missing."
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Multi-modal Vision Support
        if image_base64:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        else:
            content = prompt
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.4
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[Groq Error] Failed to generate response with {model}: {e}"

if __name__ == "__main__":
    client = GroqClient()
    print("Testing Groq:", client.generate("Are you online?", "llama-3.1-8b-instant"))
