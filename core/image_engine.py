import os
import re
import json
import time
import uuid
import random
import shutil
import logging
import requests
import config

logger = logging.getLogger("jarvis.vision")


class ImageGenerator:
    """
    Multi-Node High-Speed Vision Hub:
      - Tier 1: OpenAI DALL-E 3 (if OPENAI_API_KEY configured)
      - Tier 2: Tongyi-MAI/Z-Image-Turbo (Hugging Face Fast Diffusion Transformer)
      - Tier 3: mrfakename/Z-Image-Turbo (Mirror HF Space Node)
      - Tier 4: black-forest-labs/FLUX.1-schnell (HF Space Node)
      - Tier 5: Pollinations AI Multi-Model Grid (Seeded cache-bypass fallback)
    """

    def __init__(self):
        self.openai_client = None
        if getattr(config, "OPENAI_API_KEY", None):
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            except Exception:
                logger.warning("Vision Node: OpenAI library not found. Using Z-Image-Turbo & Cloud Grid.")

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

    def _enhance_prompt(self, prompt: str) -> str:
        """Automatically enrich and condense prompts (including long multi-paragraph briefs)."""
        # Collapse multi-line section headers and whitespace into a single coherent visual prompt
        cleaned = re.sub(r"(?m)^(?:MAIN SUBJECT|ENVIRONMENT|LIGHTING|COMPOSITION|MATERIALS AND DETAIL|CAMERA AND RENDERING|QUALITY REQUIREMENTS|Avoid|Deliver one)[^:\n]*:\s*", ", ", prompt, flags=re.IGNORECASE)
        cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")

        p_lower = cleaned.lower()

        modifications = []
        if "--ultra" in p_lower:
            modifications.append("ultra realistic, 8k resolution, photorealistic")
        if "--4k" in p_lower:
            modifications.append("highly detailed, 4k, crisp texture")
        if "--cinematic" in p_lower:
            modifications.append("cinematic lighting, dramatic shadows, movie shot")
        if "--pro" in p_lower:
            modifications.append("professional digital art, masterpiece, high fidelity")

        if "anime" in p_lower:
            modifications.append("anime style, studio ghibli, vibrant colors")
        elif ("realistic" in p_lower or "real" in p_lower) and "photorealistic" not in p_lower:
            modifications.append("photorealistic, lifelike, natural lighting, 8k detail")
        elif "cyberpunk" in p_lower and "neon" not in p_lower:
            modifications.append("cyberpunk aesthetic, neon glow, futuristic city vibes")

        clean_prompt = (
            cleaned.replace("--ultra", "")
            .replace("--4k", "")
            .replace("--cinematic", "")
            .replace("--pro", "")
            .strip()
        )
        # Cap total prompt length at 850 chars so diffusion tokenizers and APIs never reject it
        if len(clean_prompt) > 850:
            clean_prompt = clean_prompt[:850].rsplit(" ", 1)[0]
        final_prompt = clean_prompt + (", " + ", ".join(modifications) if modifications else "")
        return final_prompt

    def _extract_gradio_image_url(self, base_url: str, sse_text: str) -> str | None:
        """Parse Gradio SSE response to extract the generated image URL."""
        for line in sse_text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                raw_json = line[5:].strip()
                try:
                    data = json.loads(raw_json)
                    if not isinstance(data, list) or not data:
                        continue
                    first = data[0]
                    # Case 1: Gallery list [{"image": {"url": ...}}]
                    if isinstance(first, list) and first:
                        item = first[0]
                        if isinstance(item, dict):
                            img_obj = item.get("image") or item
                            url = img_obj.get("url")
                            path = img_obj.get("path")
                            if url:
                                return url
                            if path:
                                return f"{base_url}/gradio_api/file={path}"
                    # Case 2: Direct ImageData dict {"url": ..., "path": ...}
                    elif isinstance(first, dict):
                        url = first.get("url")
                        path = first.get("path")
                        if url:
                            return url
                        if path:
                            return f"{base_url}/gradio_api/file={path}"
                except Exception:
                    continue
        return None

    def _download_to_path(self, img_url: str, dest_path: str) -> bool:
        """Download an image URL to local disk and verify non-empty image bytes."""
        res = requests.get(img_url, headers=self.headers, stream=True, timeout=30)
        if res.status_code == 200:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                res.raw.decode_content = True
                shutil.copyfileobj(res.raw, f)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                return True
        return False

    def _try_z_image_turbo(self, prompt: str, dest_path: str) -> str | None:
        """
        Synthesize image via Tongyi-MAI/Z-Image-Turbo (or mrfakename/Z-Image-Turbo mirror)
        and black-forest-labs/FLUX.1-schnell on Hugging Face Spaces.
        Returns provider description string on success, or None on failure.
        """
        seed = random.randint(1, 999999)
        is_landscape = any(k in prompt.lower() for k in ["16:9", "landscape", "widescreen", "wide-angle"])
        z_res = "1280x720 ( 16:9 )" if is_landscape else "1024x1024 ( 1:1 )"
        w_px, h_px = (1280, 720) if is_landscape else (1024, 1024)

        gradio_nodes = [
            {
                "name": "Tongyi-MAI/Z-Image-Turbo",
                "base": "https://tongyi-mai-z-image-turbo.hf.space",
                "endpoint": "/gradio_api/call/generate",
                "payload": {"data": [prompt, z_res, seed, 8, 3.0, True, []]},
            },
            {
                "name": "Z-Image-Turbo (Mirror Node)",
                "base": "https://mrfakename-z-image-turbo.hf.space",
                "endpoint": "/gradio_api/call/generate_image",
                "payload": {"data": [prompt, h_px, w_px, 9, seed, True]},
            },
            {
                "name": "FLUX.1-schnell",
                "base": "https://black-forest-labs-flux-1-schnell.hf.space",
                "endpoint": "/gradio_api/call/infer",
                "payload": {"data": [prompt, seed, True, w_px, h_px, 4]},
            },
        ]

        for node in gradio_nodes:
            try:
                base = node["base"]
                call_url = f"{base}{node['endpoint']}"
                logger.info(f"Vision Node: Attempting synthesis via {node['name']}...")
                r1 = requests.post(call_url, json=node["payload"], headers=self.headers, timeout=12)
                if r1.status_code != 200:
                    continue
                event_id = r1.json().get("event_id")
                if not event_id:
                    continue

                r2 = requests.get(f"{call_url}/{event_id}", headers=self.headers, timeout=35)
                if r2.status_code != 200 or "event: error" in r2.text:
                    if "ZeroGPU quota" in r2.text:
                        logger.info("Vision Node: HF ZeroGPU quota reached, switching to Pollinations grid.")
                        break
                    continue

                img_url = self._extract_gradio_image_url(base, r2.text)
                if img_url and self._download_to_path(img_url, dest_path):
                    return f"Mission manifest via {node['name']}."
            except Exception as e:
                logger.warning(f"Vision Node ({node['name']}) notice: {e}")
                continue

        return None

    def _try_pollinations(self, prompt: str, dest_path: str) -> str | None:
        """Fallback to Pollinations AI with URL-length protection and burst-window pacing."""
        short_prompt = prompt[:340].rsplit(" ", 1)[0] if len(prompt) > 340 else prompt
        is_landscape = any(k in prompt.lower() for k in ["16:9", "landscape", "widescreen", "wide-angle"])
        dims = "&width=1280&height=720" if is_landscape else "&width=1024&height=1024"
        safe_prompt = requests.utils.quote(short_prompt)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?nologo=true{dims}&seed={random.randint(1, 99999)}"
        for attempt in range(4):
            try:
                res = requests.get(url, headers=self.headers, stream=True, timeout=30)
                content_type = res.headers.get("content-type", "")
                if res.status_code == 200 and "image" in content_type:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        res.raw.decode_content = True
                        shutil.copyfileobj(res.raw, f)
                    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                        return "Mission manifest via Pollinations AI acceleration grid."
                wait_sec = 3.5 + (attempt * 1.5)
                logger.info(f"Pollinations cooldown (status {res.status_code}), waiting {wait_sec:.1f}s...")
                time.sleep(wait_sec)
            except Exception as e:
                logger.warning(f"Pollinations attempt {attempt+1} failed: {e}")
                time.sleep(3.0)
        return None

    def generate(self, prompt: str):
        """Synthesize high-fidelity imagery via Z-Image-Turbo and multi-node cloud failover."""
        enhanced_prompt = self._enhance_prompt(prompt)
        logger.info(f"Vision Node: Synthesizing enhanced image: {enhanced_prompt}")

        try:
            filename = f"gen_{uuid.uuid4().hex}.png"
            path = os.path.join(config.IMAGE_GEN_DIR, filename)

            # Tier 1: OpenAI DALL-E 3 (if configured)
            if self.openai_client:
                try:
                    logger.info("Vision Node: Attempting DALL-E 3 synthesis.")
                    response = self.openai_client.images.generate(
                        model="dall-e-3",
                        prompt=enhanced_prompt,
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    )
                    image_url = response.data[0].url
                    if self._download_to_path(image_url, path):
                        return {
                            "status": "success",
                            "filename": filename,
                            "url": f"/api/assets/images/{filename}",
                            "path": path,
                            "info": "Mission manifest via OpenAI DALL-E 3.",
                        }
                except Exception as dalle_err:
                    logger.warning(f"DALL-E 3 unavailable ({dalle_err}), falling back to Z-Image-Turbo.")

            # Tier 2: Tongyi-MAI/Z-Image-Turbo & HF Fast Diffusion Grid
            info = self._try_z_image_turbo(enhanced_prompt, path)
            if info:
                return {
                    "status": "success",
                    "filename": filename,
                    "path": path,
                    "url": f"/api/assets/images/{filename}",
                    "info": info,
                }

            # Tier 3: Seeded Pollinations AI Multi-Model Grid
            info = self._try_pollinations(enhanced_prompt, path)
            if info:
                return {
                    "status": "success",
                    "filename": filename,
                    "path": path,
                    "url": f"/api/assets/images/{filename}",
                    "info": info,
                }

            raise RuntimeError("All Vision Synthesis Nodes (Z-Image-Turbo, FLUX.1-schnell, Pollinations) were temporarily unreachable.")

        except Exception as e:
            logger.error(f"Vision Hub Failure: {e}")
            return {"status": "error", "message": str(e)}
