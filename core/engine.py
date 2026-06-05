"""
Jarvis v5.0 — Asynchronous Model Engine
Non-blocking inference via Ollama SSE.
"""
import json
import httpx
import logging
import asyncio
from typing import AsyncGenerator, Dict, List, Optional
import config

logger = logging.getLogger(__name__)

class ModelEngine:
    """Manages asynchronous interaction with local Ollama models."""
    
    def __init__(self):
        self.base_url = config.OLLAMA_HOST
        self.timeout = httpx.Timeout(240.0, connect=10.0)

    async def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        model: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response (token by token) asynchronously."""
        
        # 1. Prepare Payload
        payload_messages = messages
        if system_prompt:
            payload_messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": model,
            "messages": payload_messages,
            "stream": True,
            "options": {
                "temperature": config.MODEL_TEMPERATURE,
                "num_ctx": config.CONTEXT_WINDOW,
            }
        }

        # 2. Async Inference Path
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    if response.status_code != 200:
                        yield f"⚠️ Neural Node Status: {response.status_code}"
                        return

                    async for line in response.aiter_lines():
                        if not line: continue
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                if chunk: yield chunk
                            if data.get("done", False): break
                        except json.JSONDecodeError:
                            continue
            except httpx.ConnectError:
                yield "⚠️ Link Failure: Ollama node is offline."
            except Exception as e:
                logger.error(f"Inference error: {e}")
                yield f"⚠️ Engine Pulse Failure: {str(e)}"
