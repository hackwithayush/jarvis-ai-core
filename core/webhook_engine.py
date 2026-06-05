import requests
import logging
import asyncio

logger = logging.getLogger("jarvis.webhooks")

class WebhookEngine:
    """Universal Action Node: Triggers external worlds."""
    
    def __init__(self):
        self.endpoints = {} # name -> url

    def add_endpoint(self, name, url):
        self.endpoints[name] = url
        logger.info(f"Webhook Node Registered: {name}")

    async def trigger(self, name, payload: dict):
        url = self.endpoints.get(name)
        if not url:
            logger.error(f"Webhook Node Not Found: {name}")
            return {"status": "error", "message": "Endpoint not registered."}

        try:
            # Run in worker to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=payload, timeout=10)
            )
            
            if response.status_code < 300:
                logger.info(f"Webhook {name} triggered successfully.")
                return {"status": "success", "code": response.status_code}
            else:
                logger.error(f"Webhook {name} failed: {response.status_code}")
                return {"status": "failure", "code": response.status_code}
        except Exception as e:
            logger.error(f"Webhook {name} exception: {e}")
            return {"status": "exception", "error": str(e)}

# Global Instance
webhook_engine = WebhookEngine()
