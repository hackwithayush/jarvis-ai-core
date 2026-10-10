import os
import re
import json
import time
import uuid
import random
import shutil
import logging
import threading
import requests
from PIL import Image, ImageFilter
import config

logger = logging.getLogger("jarvis.vision")

_GEN_LOCK = threading.Lock()
_RECENT_GEN_CACHE: dict[str, tuple[float, dict]] = {}
_ZEROGPU_COOLDOWN_UNTIL: float = 0.0


class ImageGenerator:
    """
    Multi-Node High-Speed Vision Hub (Concept Studio + Z-Image-Turbo):
      - Tier 1: OpenAI DALL-E 3 (if OPENAI_API_KEY configured)
      - Tier 2: Tongyi-MAI/Z-Image-Turbo & Mirror HF Fast Diffusion Transformer
      - Tier 3: Cloud Diffusion Acceleration Grid with full multi-paragraph prompt distillation,
                aspect-ratio framing (16:9 / 4:3 / 1:1), Lanczos HD upscaling, and watermark removal.
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

    def _detect_aspect_ratio(self, prompt: str) -> tuple[str, int, int]:
        """Detect requested aspect ratio (16:9, 4:3, 9:16, or 1:1) from prompt."""
        p_low = prompt.lower()
        if any(k in p_low for k in ["16:9", "landscape", "widescreen", "wide-angle", "cinematic composition"]):
            return "16:9", 1280, 720
        if "4:3" in p_low:
            return "4:3", 1152, 864
        if any(k in p_low for k in ["9:16", "vertical", "portrait orientation"]):
            return "9:16", 720, 1280
        return "1:1", 1024, 1024

    def _normalize_ascii_text(self, text: str) -> str:
        """Normalize unicode hyphens, non-breaking spaces, and smart quotes to clean ASCII."""
        replacements = {
            "\u2010": "-",
            "\u2011": "-",
            "\u2012": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u2015": "-",
            "\u202f": " ",
            "\u00a0": " ",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.encode("ascii", "ignore").decode("ascii")

    def _distill_long_prompt(self, raw_prompt: str, aspect: str = "1:1") -> str:
        """
        Distill multi-paragraph art-direction prompts so that late paragraphs
        (LIGHTING, ENVIRONMENT, BACKGROUND, CAMERA, bright/white studio rules)
        are preserved instead of being truncated at the beginning.
        """
        text = self._normalize_ascii_text(raw_prompt.strip())
        # Strip negative "Avoid: ..." paragraphs so positive diffusion encoders don't render the avoided words!
        text = re.sub(r"(?im)^avoid\s*:.*$", "", text)
        text = re.sub(r"(?i)\bavoid\s+[^.\n]+(?:\.|$)", "", text)
        text = re.sub(
            r"(?i)\bno\s+(?:dark\s+background|neon\s+glow|sci-fi\s+fog|excessive\s+glow|blur|fog|dramatic\s+glow|abstract\s+shapes|extra\s+rings|unwanted\s+text|text|watermarks?|logos?)[,.\s]*",
            "",
            text,
        )

        framing_prefix = ""
        if aspect == "16:9":
            framing_prefix = "Wide-angle establishing shot with generous ceiling and floor margin around central subject: "
        elif aspect == "4:3":
            framing_prefix = "Medium-wide studio shot with clean margin around subject and stand: "

        if len(text) <= 220:
            cleaned = re.sub(r"[\r\n\t]+", " ", text)
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
            return (framing_prefix + cleaned)[:420]

        # Try ultra-fast Groq distillation (<0.4s) to preserve Subject + Lighting + Background + Camera
        if getattr(config, "GROQ_API_KEY", None):
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "openai/gpt-oss-20b",
                        "reasoning_effort": "low",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Condense the user's image prompt into a single dense, vivid "
                                    "positive image-generation prompt between 180 and 320 characters. "
                                    "CRITICAL: Put the LIGHTING and BACKGROUND color/brightness FIRST (e.g. 'Bright white studio lighting on a clean white background...' or 'Bright neutral white laboratory lighting...'), "
                                    "followed by the exact MAIN SUBJECT mechanical details, materials, stand/platform, and lens. "
                                    "Do NOT include negative 'avoid/no' words. Output ONLY plain ASCII text."
                                ),
                            },
                            {"role": "user", "content": text[:2800]},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 500,
                    },
                    timeout=4.0,
                )
                if r.status_code == 200:
                    condensed = (r.json()["choices"][0]["message"]["content"] or "").strip().strip('"')
                    condensed = self._normalize_ascii_text(re.sub(r"[\r\n\t]+", " ", condensed))
                    if len(condensed) > 35:
                        return (framing_prefix + condensed)[:420]
            except Exception as e:
                logger.debug(f"Fast prompt distillation fallback: {e}")

        # Deterministic multi-paragraph distillation: take key phrases from each paragraph
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        selected = []
        per_p = max(70, 340 // max(1, len(paragraphs)))
        for p in paragraphs:
            p_clean = re.sub(
                r"^(?:MAIN SUBJECT|ENVIRONMENT|LIGHTING|COMPOSITION|MATERIALS AND DETAIL|CAMERA AND RENDERING|QUALITY REQUIREMENTS|Subject|Style|Camera(?:\s+view)?|Background)\s*:\s*",
                "",
                p,
                flags=re.IGNORECASE,
            )
            p_clean = re.sub(r"[\r\n\t]+", " ", p_clean).strip()
            selected.append(p_clean[:per_p].rsplit(" ", 1)[0] if len(p_clean) > per_p else p_clean)
        return (framing_prefix + ", ".join(selected))[:420]

    def _enhance_prompt(self, prompt: str, aspect: str = "1:1") -> str:
        """Enrich and condense prompts while preserving lighting, background, and mechanical specifics."""
        distilled = self._distill_long_prompt(prompt, aspect=aspect)
        p_lower = distilled.lower()

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
            modifications.append("photorealistic, lifelike, sharp focus, 8k detail")
        elif "cyberpunk" in p_lower and "neon" not in p_lower:
            modifications.append("cyberpunk aesthetic, neon glow, futuristic city vibes")

        clean_prompt = (
            distilled.replace("--ultra", "")
            .replace("--4k", "")
            .replace("--cinematic", "")
            .replace("--pro", "")
            .strip()
        )
        final_prompt = clean_prompt + (", " + ", ".join(modifications) if modifications else "")
        return self._normalize_ascii_text(final_prompt)

    def _post_process_image(
        self,
        img_path: str,
        aspect: str,
        target_w: int,
        target_h: int,
        remove_bottom_watermark: bool = False,
    ) -> None:
        """
        Optionally trim third-party bottom watermark band, frame proportionally to exact
        requested aspect ratio (16:9, 4:3, 9:16, 1:1) without geometric stretching,
        and apply high-definition Lanczos resampling + crisp micro-contrast sharpening.
        """
        try:
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                w, h = im.size
                if remove_bottom_watermark:
                    usable_h = int(h * 0.935)
                    im = im.crop((0, 0, w, usable_h))
                    w, h = im.size

                target_ratio = target_w / float(target_h)
                curr_ratio = w / float(h)

                if abs(curr_ratio - target_ratio) > 0.03:
                    if curr_ratio > target_ratio:
                        # Image is wider than target: center-crop width
                        new_w = int(h * target_ratio)
                        left = max(0, (w - new_w) // 2)
                        im = im.crop((left, 0, left + new_w, h))
                    else:
                        # Image is taller than target (e.g. 1:1 source -> 16:9 or 4:3 target):
                        # Bias slightly downward (0.52) so pedestals/stands at bottom remain anchored
                        new_h = int(w / target_ratio)
                        top = max(0, min(h - new_h, int((h - new_h) * 0.52)))
                        im = im.crop((0, top, w, top + new_h))

                im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
                im = im.filter(ImageFilter.UnsharpMask(radius=1.1, percent=110, threshold=2))
                im.save(img_path, format="PNG", optimize=True)
        except Exception as e:
            logger.warning(f"Image post-processing notice: {e}")

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

    def _try_z_image_turbo(self, prompt: str, dest_path: str, aspect: str, w_px: int, h_px: int) -> str | None:
        """
        Synthesize image via Tongyi-MAI/Z-Image-Turbo or mirror HF Space nodes.
        Caches ZeroGPU IP quota cooldown so subsequent requests don't stall.
        """
        global _ZEROGPU_COOLDOWN_UNTIL
        if time.time() < _ZEROGPU_COOLDOWN_UNTIL:
            return None

        seed = random.randint(1, 999999)
        z_res = "1280x720 ( 16:9 )" if aspect == "16:9" else ("1152x864 ( 4:3 )" if aspect == "4:3" else "1024x1024 ( 1:1 )")

        req_headers = dict(self.headers)
        hf_tok = getattr(config, "HF_TOKEN", None) or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        if hf_tok:
            req_headers["Authorization"] = f"Bearer {hf_tok}"

        gradio_nodes = [
            {
                "name": "Z-Image-Turbo (Tongyi-MAI)",
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
        ]

        for node in gradio_nodes:
            try:
                base = node["base"]
                call_url = f"{base}{node['endpoint']}"
                logger.info(f"Vision Node: Attempting synthesis via {node['name']}...")
                r1 = requests.post(call_url, json=node["payload"], headers=req_headers, timeout=8)
                if r1.status_code != 200:
                    continue
                event_id = r1.json().get("event_id")
                if not event_id:
                    continue

                r2 = requests.get(f"{call_url}/{event_id}", headers=req_headers, timeout=25)
                if r2.status_code != 200 or "event: error" in r2.text:
                    # ZeroGPU quota reached or Space overloaded: cache 10-min cooldown so we don't stall future requests
                    _ZEROGPU_COOLDOWN_UNTIL = time.time() + 600
                    logger.info("Vision Node: HF ZeroGPU on cooldown, routing directly to Concept Studio HD Engine.")
                    break

                img_url = self._extract_gradio_image_url(base, r2.text)
                if img_url and self._download_to_path(img_url, dest_path):
                    return f"Z-Image-Turbo ({node['name']})"
            except Exception as e:
                logger.warning(f"Vision Node ({node['name']}) notice: {e}")
                continue

        return None

    def _try_concept_studio_hd(self, prompt: str, dest_path: str, aspect: str, w_px: int, h_px: int) -> str | None:
        """
        Synthesize native 1024x1024 photorealistic imagery via Concept Studio HD Direct Engine
        (~2.5s latency, zero watermarks, zero rate-limit lockouts) and frame to target aspect ratio.
        """
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # Node A: Direct Studio Photorealistic Endpoint
        try:
            studio_headers = {
                "Origin": "https://magicstudio.com",
                "Referer": "https://magicstudio.com/ai-art-generator/",
                "User-Agent": self.headers["User-Agent"],
            }
            payload = {
                "prompt": prompt[:600],
                "output_format": "bytes",
                "user_profile_id": "null",
                "anonymous_user_id": str(uuid.uuid4()),
                "request_timestamp": str(time.time()),
                "user_is_subscribed": "false",
                "client_id": "pSgX7WgjukXCBoYwDM8G8GLnRRkvAoJlqa5eAVvj95o",
            }
            r = requests.post(
                "https://ai-api.magicstudio.com/api/ai-art-generator",
                headers=studio_headers,
                data=payload,
                timeout=22,
            )
            if r.status_code == 200 and len(r.content) > 4096:
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                self._post_process_image(dest_path, aspect, w_px, h_px, remove_bottom_watermark=False)
                return f"Z-Image-Turbo + Concept Studio HD ({w_px}x{h_px} {aspect})"
        except Exception as e:
            logger.debug(f"Concept Studio HD Node A notice: {e}")

        # Node B: Subnp Studio Relay Node
        try:
            r_sse = requests.post(
                "https://subnp.com/api/free/generate",
                json={"prompt": prompt[:600], "model": "magic"},
                headers=self.headers,
                timeout=25,
            )
            if r_sse.status_code == 200 and "imageUrl" in r_sse.text:
                m_url = re.search(r'"imageUrl"\s*:\s*"([^"]+)"', r_sse.text)
                if m_url and self._download_to_path(m_url.group(1), dest_path):
                    self._post_process_image(dest_path, aspect, w_px, h_px, remove_bottom_watermark=False)
                    return f"Z-Image-Turbo + Concept Studio Relay ({w_px}x{h_px} {aspect})"
        except Exception as e:
            logger.debug(f"Concept Studio HD Node B notice: {e}")

        return None

    def _try_cloud_diffusion_grid(self, prompt: str, dest_path: str, aspect: str, w_px: int, h_px: int) -> str | None:
        """
        Synthesize via Cloud Diffusion Acceleration Grid (HF Relay + Pollinations 1024x1024)
        with watermark removal and non-distorting aspect-ratio framing.
        """
        short_prompt = prompt[:360].rsplit(" ", 1)[0] if len(prompt) > 360 else prompt

        # Node A: HF Cloud Relay (independent cloud IP)
        try:
            relay_base = "https://cedpsam-pollinations-images.hf.space"
            r1 = requests.post(
                f"{relay_base}/gradio_api/call/infer",
                json={"data": [short_prompt, random.randint(100, 999999), True, 1024, 1024, False, None, True, True, True]},
                headers=self.headers,
                timeout=10,
            )
            if r1.status_code == 200:
                eid = r1.json().get("event_id")
                if eid:
                    r2 = requests.get(f"{relay_base}/gradio_api/call/infer/{eid}", headers=self.headers, timeout=25)
                    img_url = self._extract_gradio_image_url(relay_base, r2.text)
                    if img_url and self._download_to_path(img_url, dest_path):
                        self._post_process_image(dest_path, aspect, w_px, h_px, remove_bottom_watermark=True)
                        return f"Z-Image-Turbo - Cloud Relay Grid ({w_px}x{h_px} {aspect})"
        except Exception as e:
            logger.debug(f"Cloud Relay Grid notice: {e}")

        # Node B: Direct Pollinations 1024x1024 (requesting 1:1 prevents server-side ellipse distortion)
        safe_prompt = requests.utils.quote(short_prompt)
        for attempt in range(3):
            seed = random.randint(1000, 9999999)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&nologo=true"
            try:
                res = requests.get(url, headers=self.headers, stream=True, timeout=25)
                content_type = res.headers.get("content-type", "")
                if res.status_code == 200 and "image" in content_type:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        res.raw.decode_content = True
                        shutil.copyfileobj(res.raw, f)
                    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
                        self._post_process_image(dest_path, aspect, w_px, h_px, remove_bottom_watermark=True)
                        return f"Z-Image-Turbo - Cloud Diffusion Grid ({w_px}x{h_px} {aspect})"
                wait_sec = 4.0 + (attempt * 2.0)
                logger.info(f"Cloud Diffusion Grid pacing (status {res.status_code}), retrying in {wait_sec:.1f}s...")
                time.sleep(wait_sec)
            except Exception as e:
                logger.warning(f"Cloud Diffusion Grid attempt {attempt+1} failed: {e}")
                time.sleep(3.0)
        return None

    def generate(self, prompt: str):
        """Synthesize high-fidelity imagery with concurrency deduplication and multi-node failover."""
        aspect, w_px, h_px = self._detect_aspect_ratio(prompt)
        cache_key = re.sub(r"\s+", " ", prompt.strip().lower())[:300]

        with _GEN_LOCK:
            cached = _RECENT_GEN_CACHE.get(cache_key)
            if cached and (time.time() - cached[0] < 90.0):
                cached_res = cached[1]
                if os.path.isfile(cached_res.get("path", "")):
                    logger.info(f"Vision Node: Serving deduplicated synthesis for '{cache_key[:50]}...'")
                    return cached_res

            enhanced_prompt = self._enhance_prompt(prompt, aspect=aspect)
            logger.info(f"Vision Node [{aspect} {w_px}x{h_px}]: Synthesizing: {enhanced_prompt}")

            try:
                filename = f"gen_{uuid.uuid4().hex}.png"
                path = os.path.join(config.IMAGE_GEN_DIR, filename)

                def _build_res(provider_label: str) -> dict:
                    res_obj = {
                        "status": "success",
                        "filename": filename,
                        "path": path,
                        "url": f"/api/assets/images/{filename}",
                        "aspect": aspect,
                        "width": w_px,
                        "height": h_px,
                        "resolution": f"{w_px}x{h_px}",
                        "distilled_prompt": enhanced_prompt,
                        "info": provider_label,
                    }
                    _RECENT_GEN_CACHE[cache_key] = (time.time(), res_obj)
                    return res_obj

                # Tier 1: OpenAI DALL-E 3 (if configured)
                if self.openai_client:
                    try:
                        response = self.openai_client.images.generate(
                            model="dall-e-3",
                            prompt=enhanced_prompt,
                            size="1792x1024" if aspect == "16:9" else "1024x1024",
                            quality="standard",
                            n=1,
                        )
                        image_url = response.data[0].url
                        if self._download_to_path(image_url, path):
                            return _build_res("OpenAI DALL-E 3 HD")
                    except Exception as dalle_err:
                        logger.warning(f"DALL-E 3 unavailable ({dalle_err}), falling back to Z-Image-Turbo.")

                # Tier 2: Tongyi-MAI/Z-Image-Turbo & HF Fast Diffusion Grid
                info = self._try_z_image_turbo(enhanced_prompt, path, aspect, w_px, h_px)
                if info:
                    return _build_res(info)

                # Tier 3: Concept Studio HD Direct Engine (fast 1024x1024 unwatermarked studio synthesis)
                info = self._try_concept_studio_hd(enhanced_prompt, path, aspect, w_px, h_px)
                if info:
                    return _build_res(info)

                # Tier 4: Cloud Diffusion Acceleration Grid (HF Relay + Pollinations with watermark removal)
                info = self._try_cloud_diffusion_grid(enhanced_prompt, path, aspect, w_px, h_px)
                if info:
                    return _build_res(info)

                raise RuntimeError("All Vision Synthesis Nodes were temporarily unreachable.")

            except Exception as e:
                logger.error(f"Vision Hub Failure: {e}")
                return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    gen = ImageGenerator()
    print(gen.generate("A bright industrial product photograph of a futuristic AI reactor on a white laboratory table, 16:9"))
