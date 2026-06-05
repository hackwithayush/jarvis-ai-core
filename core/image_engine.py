import os
import uuid
import requests
import shutil
import tempfile
import config
import logging

logger = logging.getLogger("jarvis.vision")

class ImageGenerator:
    """Lightweight Vision Hub — Replaces heavy local models with high-speed inference."""
    
    def __init__(self):
        # Neural Path: Using DALL-E 3 for Pro-Tier and Pollinations AI for Base-Tier
        self.openai_client = None
        if config.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            except:
                logger.warning("Vision Node: OpenAI library not found. Falling back to Pollinations.")

    def _enhance_prompt(self, prompt: str) -> str:
        """SaaS Logic: Automatically enrich prompts with architectural and stylistic flags."""
        p_lower = prompt.lower()
        
        # 1. Architectural Flags
        modifications = []
        if "--ultra" in p_lower: modifications.append("ultra realistic, 8k resolution, photorealistic")
        if "--4k" in p_lower: modifications.append("highly detailed, 4k, crisp texture")
        if "--cinematic" in p_lower: modifications.append("cinematic lighting, dramatic shadows, movie shot")
        if "--pro" in p_lower: modifications.append("professional digital art, masterpiece, high fidelity")
        
        # 2. Stylistic Fallbacks
        if "anime" in p_lower: modifications.append("anime style, studio ghibli, vibrant colors")
        elif "realistic" in p_lower: modifications.append("high fidelity, lifelike, natural lighting")
        elif "cyberpunk" in p_lower: modifications.append("cyberpunk aesthetic, neon glow, futuristic city vibes")
        
        # 3. Clean and Merge
        clean_prompt = prompt.replace("--ultra", "").replace("--4k", "").replace("--cinematic", "").replace("--pro", "").strip()
        final_prompt = clean_prompt + (", " + ", ".join(modifications) if modifications else "")
        return final_prompt

    def generate(self, prompt: str):
        """Synthesize high-fidelity imagery via cloud acceleration."""
        # 1. Prompt Engineering
        prompt = self._enhance_prompt(prompt)
        logger.info(f"Vision Node: Synthesizing enhanced image: {prompt}")
        
        try:
            filename = f"gen_{uuid.uuid4().hex}.png"
            path = os.path.join(config.IMAGE_GEN_DIR, filename)
            
            # Tier 1: OpenAI DALL-E 3 (Professional Grade)
            if self.openai_client:
                logger.info("Vision Node: Attempting DALL-E 3 synthesis.")
                response = self.openai_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                image_url = response.data[0].url
                # Download for local archive
                img_data = requests.get(image_url).content
                with open(path, 'wb') as f:
                    f.write(img_data)
                
                return {
                    "status": "success",
                    "filename": filename,
                    "url": image_url, # Direct URL is faster for initial display
                    "path": path,
                    "info": "Mission manifest via OpenAI DALL-E 3."
                }

            # Tier 2: Pollinations AI (High-Speed Fallback)
            logger.info("Vision Node: Falling back to Pollinations AI synthesis.")
            safe_prompt = requests.utils.quote(prompt)
            url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=1024&seed={uuid.uuid4().int % 1000000}&model=flux"
            
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
            else:
                raise Exception(f"Vision Hub returned status {response.status_code}")
                
            return {
                "status": "success", 
                "filename": filename,
                "path": path,
                "url": f"/api/assets/images/{filename}",
                "info": "Mission manifest via Pollinations AI acceleration grid."
            }

        except Exception as e:
            logger.error(f"Vision Hub Failure: {e}")
            return {"status": "error", "message": str(e)}
