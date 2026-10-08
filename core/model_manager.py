"""
Model Manager — Ollama Integration Layer
Handles model communication, streaming, health checks, and model management.
"""
import json
import logging
import subprocess
import time
import requests
import threading
from typing import Generator, Optional
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

import config
from core.utils import retry_sync

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages communication with the Ollama server and AI models."""

    def __init__(self):
        self.nodes = config.OLLAMA_NODES
        self._current_node_idx = 0
        self.current_model = config.DEFAULT_MODEL
        self.temperature = config.MODEL_TEMPERATURE
        self.top_p = config.MODEL_TOP_P
        self.context_window = config.CONTEXT_WINDOW
        self.quantization = getattr(config, "QUANTIZATION", "q4_k_m")
        self._available_models = []
        
        # Health Intelligence Node
        self._health_cache = {} 
        self._health_lock = threading.Lock()
        
        # Initialize External Brains
        self.openai_client = None
        if OpenAI and config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("Intelligence Hub: External Prime (OpenAI) Node Link Active.")

        # Initialize Gemini Brain (FREE flagship)
        self.gemini_client = None
        if genai and config.GEMINI_API_KEY:
            self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
            logger.info("Intelligence Hub: Gemini Flash Node Link Active (FREE Flagship).")

        # Initialize OpenRouter Brain
        self.openrouter_client = None
        if OpenAI and config.OPENROUTER_API_KEY:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=config.OPENROUTER_API_KEY,
            )
            logger.info("Intelligence Hub: OpenRouter API Node Link Active.")

        # Initialize Together AI Brain
        self.together_client = None
        if OpenAI and config.TOGETHER_API_KEY:
            self.together_client = OpenAI(
                base_url="https://api.together.xyz/v1",
                api_key=config.TOGETHER_API_KEY,
            )
            logger.info("Intelligence Hub: Together AI Node Link Active.")
            
        # Launch Proactive Health Monitoring
        self._exhausted_models = {}
        threading.Thread(target=self._health_monitor_loop, daemon=True).start()

    @property
    def host(self):
        """Current target Ollama node."""
        return self.nodes[self._current_node_idx % len(self.nodes)]

    # ─── Health & Connectivity ──────────────────────────────────────

    def is_ollama_running(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _health_monitor_loop(self):
        """Background thread: Periodically audit the health of all intelligence nodes."""
        logger.info("Health Monitor Node: Pulse check activated.")
        while True:
            try:
                with self._health_lock:
                    # 1. Check Local Node
                    self._health_cache["local_server"] = self.is_ollama_running()
                    
                    # 2. Check Specific Local Models
                    if self._health_cache["local_server"]:
                        models = self.list_models()
                        for m in models:
                            self._health_cache[f"model_{m['name']}"] = True
                    
                    # 3. Check Cloud Nodes
                    if config.OPENAI_API_KEY:
                        self._health_cache["openai"] = True
                    if config.GROQ_API_KEY:
                        self._health_cache["groq"] = True
                    if config.GEMINI_API_KEY:
                        self._health_cache["gemini"] = True
                        
                # Sleep between audits
                time.sleep(300) # 5 minutes
            except Exception as e:
                logger.error(f"Health Monitor Pulse Error: {e}")
                time.sleep(60)

    def _is_gemini_model(self, model_name: str) -> bool:
        """Check if a model name is a Gemini model."""
        return "gemini" in model_name.lower()

    def is_healthy(self, model_name: str) -> bool:
        """Query the health cache for a specific node/model."""
        if self._exhausted_models.get(model_name, 0) > time.time():
            return False

        if config.SERVER_MODE and ("gpt" in model_name or "groq" in model_name or "gemini" in model_name):
            return True # Assume healthy unless marked in _exhausted_models
            
        with self._health_lock:
            # Check for generic node health
            if "gemini" in model_name: return self._health_cache.get("gemini", True)
            if "gpt" in model_name: return self._health_cache.get("openai", True)
            if "groq" in model_name: return self._health_cache.get("groq", True)
            
            # Check for specific local model health
            if not self._health_cache.get("local_server", True):
                return False
            return self._health_cache.get(f"model_{model_name}", True)

    def start_ollama_server(self) -> bool:
        """Attempt to start the Ollama server."""
        try:
            logger.info("Attempting to start Ollama server...")
            import platform
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if platform.system() == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            subprocess.Popen(["ollama", "serve"], **kwargs)
            # Wait for server to be ready
            for _ in range(30):
                time.sleep(1)
                if self.is_ollama_running():
                    logger.info("Ollama server started successfully.")
                    return True
            logger.error("Ollama server failed to start within 30 seconds.")
            return False
        except FileNotFoundError:
            logger.error("Ollama is not installed. Please install from https://ollama.com/download")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    def ensure_running(self):
        """Check if Ollama is running and responsive. Skips in SERVER_MODE."""
        if config.SERVER_MODE:
            logger.info("Cloud Deployment (SERVER_MODE): Skipping local Ollama check.")
            return True

        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    # ─── Model Management ──────────────────────────────────────────

    def list_models(self) -> list[dict]:
        """List all locally available models."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self._available_models = data.get("models", [])
                return [
                    {
                        "name": m["name"],
                        "size": self._format_size(m.get("size", 0)),
                        "modified": m.get("modified_at", ""),
                        "family": m.get("details", {}).get("family", "unknown"),
                        "parameters": m.get("details", {}).get("parameter_size", "unknown"),
                    }
                    for m in self._available_models
                ]
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def pull_model(self, model_name: str) -> Generator[dict, None, None]:
        """Pull/download a model with progress updates."""
        try:
            resp = requests.post(
                f"{self.host}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=3600,
            )
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    yield {
                        "status": data.get("status", ""),
                        "completed": data.get("completed", 0),
                        "total": data.get("total", 0),
                    }
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            yield {"status": f"Error: {e}", "completed": 0, "total": 0}

    def has_model(self, model_name: str) -> bool:
        """Check if a specific model is available locally."""
        models = self.list_models()
        return any(model_name in m["name"] for m in models)

    def ensure_model(self, model_name: Optional[str] = None) -> str:
        """Ensure at least one model is available. Returns available model name."""
        model_name = model_name or self.current_model
        
        if config.SERVER_MODE:
            return model_name
            
        # Only fetch models once to prevent timeout stacking if node is offline
        models = self.list_models()
        model_names = [m["name"] for m in models]
        
        def _has(name: str) -> bool:
            return any(name in m for m in model_names)

        if _has(model_name):
            self.current_model = model_name
            return model_name
            
        # Try fallback models
        for fallback in config.FALLBACK_MODELS:
            if _has(fallback):
                logger.info(f"Using fallback model: {fallback}")
                self.current_model = fallback
                return fallback

        # No model available — trigger an asynchronous pull
        logger.warning(f"Required model '{model_name}' not found. Initializing background pull...")
        # We can't easily wait for a full pull here without blocking bot startup, 
        # so we trigger it and return the name anyway (the next request might fail but the pull will be in progress)
        # Better: Pull return the first available model in the list as a temporary bridge.
        models = self.list_models()
        if models:
            bridge_model = models[0]["name"]
            logger.info(f"Using '{bridge_model}' as a temporary bridge while '{model_name}' pulls.")
            # Trigger background pull (no-wait)
            import threading
            threading.Thread(target=lambda: list(self.pull_model(model_name)), daemon=True).start()
            return bridge_model

        return ""

    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model."""
        if self.has_model(model_name):
            self.current_model = model_name
            logger.info(f"Switched to model: {model_name}")
            return True
        return False

    # ─── Chat / Generation ─────────────────────────────────────────

    # ─── Model Routing ──────────────────────────────────────────────
    
    def route_model(self, message: str, user_tier: str = "free") -> str:
        """Intelligent Task Routing Node — Uses config.smart_route for autonomous selection."""
        # 1. High Context Override
        if len(message.split()) > 400:
            return config.ROUTING_CONFIG.get("reasoning", "llama3.1:8b")

        # 2. Autonomous Smart Routing
        target_key = config.smart_route(message)
        logger.info(f"Autonomous Routing: Redirecting mission to '{target_key}' node.")
        
        return config.ROUTING_CONFIG.get(target_key, config.ROUTING_CONFIG["chat"])

    @retry_sync(retries=2, delay=1.0)
    def generate_vision(self, prompt: str, image_path: str) -> str:
        """Analyze an image using a multimodal model (Cloud or Local)."""
        import base64
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
                base64_image = base64.b64encode(image_bytes).decode("utf-8")

            # --- Choice A: Gemini (FREE multimodal) ---
            if self.gemini_client:
                model = config.ROUTING_CONFIG.get("vision", "gemini-2.5-flash")
                logger.info(f"Vision Node Active: Analyzing image with {model} (Gemini FREE)")
                try:
                    import mimetypes
                    mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
                    response = self.gemini_client.models.generate_content(
                        model=model,
                        contents=[
                            genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            prompt
                        ],
                        config=genai_types.GenerateContentConfig(
                            system_instruction=config.SYSTEM_PROMPT.format(current_date="today"),
                            temperature=self.temperature,
                        )
                    )
                    return response.text
                except Exception as e:
                    logger.warning(f"Gemini Vision failed: {e}. Falling back...")

            # --- Choice B: OpenAI Prime (Cloud) ---
            if self.openai_client:
                model = config.ROUTING_CONFIG.get("vision", "gpt-4o")
                logger.info(f"Vision Node Active: Analyzing image with {model} (OpenAI)")
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": config.SYSTEM_PROMPT.format(current_date="today")},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                                },
                            ],
                        }
                    ],
                    max_tokens=500,
                )
                return response.choices[0].message.content

            # --- Choice C: Ollama (Local) ---
            model = config.ROUTING_CONFIG.get("local_vision", "llava")
            logger.info(f"Vision Node Active: Analyzing image with {model} (Local)")
            
            payload = {
                "model": model,
                "prompt": prompt,
                "system": config.SYSTEM_PROMPT.format(current_date="today"),
                "images": [base64_image],
                "stream": False
            }
            
            resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("response", "Vision processing complete, but no text response returned.")
            elif resp.status_code == 404:
                self.ensure_model(model)
                return f"Vision model '{model}' is being downloaded. Please wait a few minutes and try again."
            else:
                return f"Vision Node failure: HTTP {resp.status_code}"

        except Exception as e:
            logger.error(f"Vision Error: {e}")
            return f"Vision processing failed: {e}"

    def generate_stream(
        self, 
        messages: list, 
        system_prompt: str, 
        model_override: str = None, 
        user_tier: str = "free",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[list] = None,
        response_format: Optional[dict] = None
    ) -> Generator[str, None, None]:
        """Generate a streaming response with hybrid Cloud/Local routing and robust fallbacks."""
        primary_model = model_override or self.route_model(messages[-1]["content"] if messages else "", user_tier)
        
        # Neural Parameters: Apply overrides for Raw/Uncensored missions
        active_temp = temperature or self.temperature
        active_p = top_p or self.top_p
        
        if config.UNCENSORED_MODE:
            active_temp = max(active_temp, 0.8)
            active_p = min(active_p, 0.95)

        # 0. Local Ollama Priority Check (Direct offline inference if available)
        is_local_ollama_req = any(lm in primary_model.lower() for lm in ["llama2-uncensored", "uncensored", "llama3.2", "ollama"])
        if is_local_ollama_req and self.is_ollama_running():
            ollama_target = "llama2-uncensored:latest" if ("llama2" in primary_model.lower() or "uncensored" in primary_model.lower()) else ("llama3.2:latest" if "llama3.2" in primary_model.lower() else primary_model)
            logger.info(f"Ollama Local Priority: Streaming via local node '{ollama_target}'...")
            payload = {
                "model": ollama_target,
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "stream": True,
                "options": {
                    "temperature": active_temp,
                    "top_p": active_p,
                    "num_ctx": 4096,
                }
            }
            try:
                resp = requests.post(f"{self.host}/api/chat", json=payload, stream=True, timeout=(5, 300))
                if resp.status_code == 200:
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                            if data.get("done"):
                                return
                    return
            except Exception as e:
                logger.warning(f"Local Ollama stream failed for {ollama_target}: {e}. Proceeding with cloud fallbacks.")
        
        # 1. Server Mode / Cloud Priority Path with Multi-Provider Auto-Failover
        if config.SERVER_MODE:
            cloud_candidates = [primary_model] + config.FALLBACK_CHAIN
            seen = set()
            unique_cloud_models = [m for m in cloud_candidates if m and not (m in seen or seen.add(m))]
            last_cloud_error = "No available cloud nodes responded."
            
            for m in unique_cloud_models:
                # Proactively skip exhausted cloud models (e.g. 429 quota exhaustion)
                if self._exhausted_models.get(m, 0) > time.time():
                    logger.info(f"Proactive Skip: Cloud node '{m}' is in cooldown/exhausted.")
                    continue
                try:
                    logger.info(f"Cloud Intelligence Grid: Streaming via node '{m}'...")
                    
                    # A. Gemini (Google AI Studio) - Flagship priority & Multimodal
                    if self._is_gemini_model(m) and self.gemini_client:
                        yield from self._generate_gemini_stream(messages, system_prompt, model=m, response_format=response_format)
                        return

                    # B. Groq Acceleration Grid (Ultra-fast models hosted on Groq)
                    elif (m in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "allam-2-7b"] or (not ("/" in m) and not self._is_gemini_model(m))) and config.GROQ_API_KEY:
                        yield from self._generate_groq_stream(messages, system_prompt, model=m, response_format=response_format)
                        return
                    
                    # C. OpenRouter (Multi-model: Llama 3.3, DeepSeek, etc.)
                    elif self.openrouter_client and ("/" in m or "llama" in m.lower() or "deepseek" in m.lower()):
                        yield from self._generate_openrouter_stream(messages, system_prompt, model=m, response_format=response_format)
                        return
                        
                    # D. OpenAI Prime
                    elif config.OPENAI_API_KEY:
                        yield from self._generate_openai_stream(messages, system_prompt, model=m)
                        return
                        
                except Exception as e:
                    err_str = str(e)
                    last_cloud_error = err_str
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        self._exhausted_models[m] = time.time() + 3600
                    elif "402" in err_str or "credit" in err_str.lower() or "payment" in err_str.lower():
                        self._exhausted_models[m] = time.time() + 86400  # 24h cooldown for unpaid/insufficient credit models
                    elif "503" in err_str or "UNAVAILABLE" in err_str:
                        self._exhausted_models[m] = time.time() + 180
                    elif "404" in err_str or "NOT_FOUND" in err_str:
                        self._exhausted_models[m] = time.time() + 86400
                    logger.warning(f"Cloud Node '{m}' failed ({e}). Auto-healing over to next provider in fallback chain...")
                    continue

            # In SERVER_MODE, do not attempt local Ollama if it is unreachable
            if not self.is_ollama_running():
                error_msg = f"⚠️ All Cloud Intelligence Nodes failed. Traceback: {last_cloud_error}"
                logger.error(error_msg)
                yield error_msg
                return

        # 2. Local-First Path (Default) with fallback loop
        models_to_try = [primary_model] + config.FALLBACK_CHAIN
        # Remove duplicates while preserving order
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        last_error = ""
        for model in unique_models:
            # --- PROACTIVE SKIP: Don't even try if we know it's dead ---
            if not self.is_healthy(model):
                logger.info(f"Proactive Skip: Node {model} is currently offline.")
                continue

            logger.info(f"Attempting routing to Intelligence Node: {model}")
            
            try:
                # --- A0: Handle Gemini Models ---
                if self._is_gemini_model(model) and self.gemini_client:
                    try:
                        yield from self._generate_gemini_stream(messages, system_prompt, model=model)
                        return
                    except Exception as e:
                        logger.error(f"Gemini Node Error ({model}): {e}. Trying next model.")
                        last_error = str(e)
                        continue

                # --- A: Handle Cloud Models in Local Mode (OpenAI compatible) ---
                if any(m in model.lower() for m in ["gpt", "deepseek", "ling"]):
                    if self.openai_client:
                        try:
                            user_msg_content = messages[-1]["content"] if messages else ""
                            kwargs = {
                                "model": model,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_msg_content}
                                ],
                                "stream": True,
                                "timeout": 10,
                            }
                            if response_format:
                                kwargs["response_format"] = response_format
                                
                            stream = self.openai_client.chat.completions.create(**kwargs)
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    yield chunk.choices[0].delta.content
                            return # Success
                        except Exception as e:
                            logger.error(f"Cloud Brain Error ({model}): {e}. Trying next model.")
                            last_error = str(e)
                            continue

                # --- B: Handle Local Models (Ollama) ---
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                        "num_ctx": self.context_window,
                        "num_thread": 4, # Optimized for 16GB consumer CPUs
                        "num_gpu": 1 if config.VRAM_PROFILE != "eco" else 0,
                        "num_kv_seq_len": config.QUANTIZATION
                    },
                }
                payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]

                # Distributed Load Balancing (Round-Robin)
                target_node = self.nodes[self._current_node_idx % len(self.nodes)]
                self._current_node_idx += 1
                
                from core.utils import retry_sync
                
                @retry_sync(retries=2, delay=1.0)
                def execute_local_request():
                    return requests.post(f"{target_node}/api/chat", json=payload, stream=True, timeout=(3, 300))
                
                resp = execute_local_request()
                
                if resp.status_code != 200:
                    logger.warning(f"Ollama failure ({resp.status_code}) for '{model}'.")
                    last_error = f"HTTP {resp.status_code}"
                    continue

                # Success path
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            if chunk:
                                yield chunk
                        if data.get("done", False):
                            break
                return # Successfully finished a model stream

            except requests.ConnectionError:
                logger.warning(f"Cannot connect to Ollama for model {model}.")
                last_error = "Connection Error"
                continue
            except Exception as e:
                logger.error(f"Generation error ({model}): {e}")
                last_error = str(e)
                continue

        # If we get here, all models failed
        error_msg = f"⚠️ All Intelligence Nodes failed. Traceback: {last_error}"
        logger.error(error_msg)
        yield error_msg

    def _generate_openai_stream(self, messages: list, system_prompt: str, model: str = None) -> Generator[str, None, None]:
        """OpenAI-specific streaming implementation."""
        logger.info(f"Routing to OpenAI Neural Node ({model})...")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            
            payload = [{"role": "system", "content": system_prompt}] + messages
            
            kwargs = {
                "model": model or config.ROUTING_CONFIG.get("prime", "gpt-4o-mini"),
                "messages": payload,
                "stream": True,
                "temperature": config.MODEL_TEMPERATURE
            }
            if response_format:
                kwargs["response_format"] = response_format
                
            response = client.chat.completions.create(**kwargs)
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI link breakdown: {e}")
            yield f"⚠️ Neural Link Breakdown (OpenAI): {str(e)}"

    def _generate_openrouter_stream(self, messages: list, system_prompt: str, model: str = None, response_format: Optional[dict] = None) -> Generator[str, None, None]:
        """OpenRouter streaming implementation with message sanitization and credit guard."""
        logger.info(f"Routing to OpenRouter Node ({model})...")
        try:
            # Sanitize messages: discard empty content and error banners
            sanitized = []
            for msg in messages:
                c = (msg.get("content") or "").strip()
                if c and not c.startswith("⚠️"):
                    sanitized.append({"role": msg.get("role", "user"), "content": c})
            if not sanitized:
                sanitized = [{"role": "user", "content": "Hello"}]

            payload = [{"role": "system", "content": system_prompt}] + sanitized
            kwargs = {
                "model": model or config.ROUTING_CONFIG.get("flagship", "z-ai/glm-5.2"),
                "messages": payload,
                "stream": True,
                "temperature": config.MODEL_TEMPERATURE,
                "max_tokens": 2048, # Safe token cap to prevent 402 insufficient credit errors
            }
            if response_format:
                kwargs["response_format"] = response_format
            response = self.openrouter_client.chat.completions.create(**kwargs)
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenRouter breakdown ({model}): {e}")
            raise

    def _generate_together_stream(self, messages: list, system_prompt: str, model: str = None) -> Generator[str, None, None]:
        """Together AI streaming implementation."""
        logger.info(f"Routing to Together AI Node ({model})...")
        try:
            sanitized = []
            for msg in messages:
                c = (msg.get("content") or "").strip()
                if c and not c.startswith("⚠️"):
                    sanitized.append({"role": msg.get("role", "user"), "content": c})
            if not sanitized:
                sanitized = [{"role": "user", "content": "Hello"}]

            payload = [{"role": "system", "content": system_prompt}] + sanitized
            kwargs = {
                "model": model or config.ROUTING_CONFIG.get("reasoning", "deepseek-ai/DeepSeek-R1"),
                "messages": payload,
                "stream": True,
                "temperature": config.MODEL_TEMPERATURE,
                "max_tokens": 2048,
            }
            response = self.together_client.chat.completions.create(**kwargs)
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Together AI breakdown: {e}")
            yield f"⚠️ Neural Link Breakdown (Together AI): {str(e)}"

    def _generate_groq_stream(self, messages: list, system_prompt: str, model: str = None, tools: Optional[list] = None, response_format: Optional[dict] = None) -> Generator[str, None, None]:
        """Immortal Groq streaming node with auto-healing fallbacks."""
        # --- PRO LIST OF STABLE MODELS CURRENTLY ACTIVE ON GROQ ---
        SAFE_MODELS = [
            model, # Try requested first
            "openai/gpt-oss-120b", # Flagship 120B on Groq: huge context headroom & rich output
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b",
        ]
        
        # Clean unique list (remove None/empty and models known not to be on Groq)
        FALLBACKS = []
        for m in SAFE_MODELS:
            if m and m not in FALLBACKS and not any(k in m for k in ["gemini", "z-ai", "deepseek-ai"]):
                FALLBACKS.append(m)

        # Sanitize messages
        sanitized = []
        for msg in messages:
            c = (msg.get("content") or "").strip()
            if c and not c.startswith("⚠️"):
                sanitized.append({"role": msg.get("role", "user"), "content": c})
        if not sanitized:
            sanitized = [{"role": "user", "content": "Hello"}]

        # Groq Context Guard: Bound system prompt and history to fit Groq context windows
        # Truncate overly long system_prompt (e.g. huge file contexts or excessive transcripts)
        safe_sys = system_prompt
        if len(safe_sys) > 16000:
            safe_sys = safe_sys[:16000] + "\n[System prompt trimmed for token budget]"

        # Ensure sanitized messages don't exceed model limits (keep latest user input intact)
        trimmed_messages = []
        for idx, m in enumerate(sanitized):
            content = m["content"]
            # If an individual history message is excessively huge, truncate it
            if len(content) > 12000 and idx < len(sanitized) - 1:
                content = content[:12000] + "\n...[truncated prior message context]"
            elif len(content) > 24000: # Final turn safety cap
                content = content[:24000] + "\n...[truncated input to fit token budget]"
            trimmed_messages.append({"role": m["role"], "content": content})

        payload = [{"role": "system", "content": safe_sys}] + trimmed_messages
        last_error = ""

        # Attempt the Immortal Loop
        for current_node in FALLBACKS:
            try:
                # Map decommissioned or local names to safe cloud IDs
                mapping = {
                    "phi3:mini": "openai/gpt-oss-20b",
                    "llama3.1:8b": "openai/gpt-oss-20b",
                    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
                    "llama-3.1-70b-versatile": "openai/gpt-oss-120b",
                    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
                    "deepseek-v3": "openai/gpt-oss-120b",
                    "deepseek-coder:6.7b": "qwen/qwen3.8-27b",
                    "mixtral-8x7b-32768": "openai/gpt-oss-120b",
                }
                mapped_model = mapping.get(current_node, current_node)
                
                logger.info(f"Intelligence Grid: Routing Mission to node '{mapped_model}'")
                
                from openai import OpenAI
                client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=config.GROQ_API_KEY)
                
                # Model-Specific Payload Guard: Qwen 3.8 on Groq has a strict 7000 ITPM limit
                model_payload = list(payload)
                if "qwen" in mapped_model.lower():
                    total_chars = sum(len(m.get("content", "")) for m in model_payload)
                    if total_chars > 16000:
                        sys_content = model_payload[0]["content"]
                        if len(sys_content) > 6000:
                            sys_content = sys_content[:6000] + "\n[System prompt compressed for Qwen ITPM ceiling]"
                        recent_msgs = model_payload[1:][-4:]
                        model_payload = [{"role": "system", "content": sys_content}] + recent_msgs

                # Estimate total characters in payload to avoid context boundary overrun
                approx_chars = sum(len(m.get("content", "")) for m in model_payload)
                # Adaptive max_tokens: Allow full 4096 tokens for 120B to avoid truncation on large lists
                if "qwen" in mapped_model.lower():
                    calc_max_tokens = 1500
                elif "oss-20b" in mapped_model.lower():
                    calc_max_tokens = 2048
                else:
                    calc_max_tokens = 4096
                
                kwargs = {
                    "model": mapped_model,
                    "messages": model_payload,
                    "stream": True,
                    "temperature": config.MODEL_TEMPERATURE,
                    "max_tokens": calc_max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                    
                response = client.chat.completions.create(**kwargs)
                
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return # Successful completion

            except Exception as e:
                err_text = str(e)
                logger.warning(f"Intelligence Node '{current_node}' failed: {err_text}. Initiating redirection...")
                last_error = err_text
                
                # If error is due to message/completion length, try with aggressively trimmed payload on next model
                if "reduce the length" in err_text.lower() or "too large" in err_text.lower():
                    if len(payload) > 1 and len(payload[0]["content"]) > 6000:
                        payload[0]["content"] = payload[0]["content"][:6000] + "\n[Context compressed]"
                continue

        # If all Groq models failed, raise to let generate_stream failover to OpenRouter / Cloud
        raise RuntimeError(f"All Groq models failed: {last_error}")

    def _generate_gemini_stream(self, messages: list, system_prompt: str, model: str = None, response_format: Optional[dict] = None) -> Generator[str, None, None]:
        """Gemini-specific streaming implementation with multi-turn structure enforcement and model auto-failover."""
        target_model = model or config.ROUTING_CONFIG.get("flagship", "gemini-2.5-flash")
        if not self._is_gemini_model(target_model):
            target_model = "gemini-2.5-flash"

        # Map defunct/retired models to currently active models
        if target_model in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]:
            target_model = "gemini-2.5-flash"

        if not self.gemini_client:
            raise RuntimeError("Gemini client not initialized. Check GEMINI_API_KEY.")

        # Candidate Gemini models in priority order
        candidates = [target_model]
        for alt in ["gemini-2.5-flash", "gemini-3.8-flash"]:
            if alt not in candidates:
                candidates.append(alt)

        # Build sanitized, strictly alternating Content array conforming to Gemini API rules
        contents = []
        for msg in messages:
            if msg.get("role") == "system":
                continue
            role = "model" if msg.get("role") == "assistant" else "user"
            raw_text = (msg.get("content") or "").strip()
            # Omit error banners and empty content
            if not raw_text or raw_text.startswith("⚠️"):
                continue

            # Merge consecutive turns with the same role into one Content block
            if contents and contents[-1].role == role:
                contents[-1].parts.append(genai_types.Part.from_text(text=raw_text))
            else:
                contents.append(genai_types.Content(role=role, parts=[genai_types.Part.from_text(text=raw_text)]))

        # Gemini Rule 1: Contents cannot be empty
        if not contents:
            contents = [genai_types.Content(role="user", parts=[genai_types.Part.from_text(text="Hello")])]

        # Gemini Rule 2: First turn must be 'user'
        while contents and contents[0].role != "user":
            contents.pop(0)

        if not contents:
            contents = [genai_types.Content(role="user", parts=[genai_types.Part.from_text(text="Hello")])]

        # Gemini Rule 3: Last turn MUST be 'user' (never 'model')
        if contents[-1].role != "user":
            user_text = ""
            if messages:
                user_text = (messages[-1].get("content") or "").strip()
            if not user_text:
                user_text = "Please continue."
            contents.append(genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_text)]))

        cfg_kwargs = {
            "system_instruction": system_prompt,
            "temperature": config.MODEL_TEMPERATURE,
            "top_p": config.MODEL_TOP_P,
        }
        if response_format and response_format.get("type") == "json_object":
            cfg_kwargs["response_mime_type"] = "application/json"

        last_gemini_err = None
        for m in candidates:
            if self._exhausted_models.get(m, 0) > time.time():
                continue
            try:
                logger.info(f"Intelligence Grid: Routing to Gemini Node ({m})...")
                for chunk in self.gemini_client.models.generate_content_stream(
                    model=m,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(**cfg_kwargs)
                ):
                    if chunk.text:
                        yield chunk.text
                return # Completed stream successfully
            except Exception as e:
                err_s = str(e)
                logger.warning(f"Gemini candidate '{m}' failed: {err_s}")
                last_gemini_err = e
                if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s:
                    self._exhausted_models[m] = time.time() + 3600
                elif "503" in err_s or "UNAVAILABLE" in err_s:
                    self._exhausted_models[m] = time.time() + 60
                elif "404" in err_s or "NOT_FOUND" in err_s:
                    self._exhausted_models[m] = time.time() + 86400
                continue

        if last_gemini_err:
            raise last_gemini_err

    @retry_sync(retries=2, delay=0.5)
    def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        model: Optional[str] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """Generate a complete (non-streaming) response with error reporting."""
        chunks = []
        for chunk in self.generate_stream(messages, system_prompt, model, response_format=response_format):
            chunks.append(chunk)
        
        result = "".join(chunks)
        if result.startswith("⚠️"):
            # If all else fails, don't return partial error as valid response
            logger.error(f"Primary model generation failed completely: {result}")
            return f"Error: I'm currently unable to process this request. ({result})"
        return result

    def purge_context(self, model_name: str):
        """Neural Purge: Force Ollama to release VRAM/RAM for a specific model."""
        try:
            logger.info(f"Neural Purge: Clearing context cache for {model_name}...")
            requests.post(f"{self.host}/api/generate", json={"model": model_name, "keep_alive": 0})
        except Exception as e:
            logger.error(f"Purge Failure: {e}")

    # ─── Utilities ──────────────────────────────────────────────────

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def get_status(self) -> dict:
        """Get current status summary."""
        running = self.is_ollama_running()
        models = self.list_models() if running else []
        return {
            "ollama_running": running,
            "current_model": self.current_model,
            "available_models": models,
            "model_count": len(models),
            "temperature": self.temperature,
            "host": self.host,
        }
