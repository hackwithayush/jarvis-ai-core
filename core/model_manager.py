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
            
        # Launch Proactive Health Monitoring
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
        if config.SERVER_MODE and ("gpt" in model_name or "groq" in model_name or "gemini" in model_name):
            return True # Always assume cloud is target in server mode
            
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
        
        # 1. Server Mode / Cloud Priority Path
        if config.SERVER_MODE:
            try:
                # Gemini models route to Gemini API
                if self._is_gemini_model(primary_model) and self.gemini_client:
                    yield from self._generate_gemini_stream(messages, system_prompt, model=primary_model)
                    return
                elif config.GROQ_API_KEY:
                    yield from self._generate_groq_stream(messages, system_prompt, model=primary_model)
                    return
                elif config.OPENAI_API_KEY:
                    yield from self._generate_openai_stream(messages, system_prompt, model=primary_model)
                    return
            except Exception as e:
                logger.error(f"Cloud Priority Node Failure: {e}. Falling back to Local Neural Node.")
                # Don't return here, fall through to Local Path as a safety net if available

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

    def _generate_groq_stream(self, messages: list, system_prompt: str, model: str = None, tools: Optional[list] = None, response_format: Optional[dict] = None) -> Generator[str, None, None]:
        """Immortal Groq streaming node with auto-healing fallbacks."""
        # --- PRO LIST OF STABLE MODELS ---
        SAFE_MODELS = [
            model, # Try requested first
            config.ROUTING_CONFIG.get("chat"),
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]
        
        # Clean unique list (remove None/empty)
        FALLBACKS = []
        for m in SAFE_MODELS:
            if m and m not in FALLBACKS:
                FALLBACKS.append(m)

        payload = [{"role": "system", "content": system_prompt}] + messages
        last_error = ""

        # Attempt the Immortal Loop
        for current_node in FALLBACKS:
            try:
                # Map decommissioned or local names to safe cloud IDs
                mapping = {
                    "phi3:mini": "llama-3.1-8b-instant",
                    "llama3.1:8b": "llama-3.1-8b-instant",
                    "deepseek-v3": "llama-3.3-70b-versatile",
                    "deepseek-coder:6.7b": "llama-3.3-70b-versatile",
                    "llama-3.1-70b-versatile": "llama-3.3-70b-versatile"
                }
                mapped_model = mapping.get(current_node, current_node)
                
                logger.info(f"Intelligence Grid: Routing Mission to node '{mapped_model}'")
                
                from openai import OpenAI
                client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=config.GROQ_API_KEY)
                
                kwargs = {
                    "model": mapped_model,
                    "messages": payload,
                    "stream": True,
                    "temperature": config.MODEL_TEMPERATURE
                }
                if response_format:
                    kwargs["response_format"] = response_format
                    
                response = client.chat.completions.create(**kwargs)
                
                for chunk in response:
                    logger.info(f"GROQ RAW CHUNK: {chunk}")
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return # Successful completion

            except Exception as e:
                logger.warning(f"Intelligence Node '{current_node}' failed: {e}. Initiating redirection...")
                last_error = str(e)
                continue

        # Terminal Failsafe: Try Gemini → OpenAI if Groq is totally down
        if self.gemini_client:
            try:
                yield from self._generate_gemini_stream(messages, system_prompt)
                return
            except Exception:
                pass
        if config.OPENAI_API_KEY:
            yield from self._generate_openai_stream(messages, system_prompt)
        else:
            yield f"⚠️ All Neural Nodes offline. Last breakdown: {last_error}"

    def _generate_gemini_stream(self, messages: list, system_prompt: str, model: str = None) -> Generator[str, None, None]:
        """Gemini-specific streaming implementation (FREE flagship tier)."""
        model = model or config.ROUTING_CONFIG.get("flagship", "gemini-2.5-flash")
        logger.info(f"Intelligence Grid: Routing to Gemini Node ({model})...")
        try:
            if not self.gemini_client:
                raise RuntimeError("Gemini client not initialized. Check GEMINI_API_KEY.")

            # Build content from messages
            user_content = messages[-1]["content"] if messages else ""

            for chunk in self.gemini_client.models.generate_content_stream(
                model=model,
                contents=user_content,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=config.MODEL_TEMPERATURE,
                    top_p=config.MODEL_TOP_P,
                )
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini Node Failure: {e}")
            yield f"⚠️ Gemini Neural Link Breakdown: {str(e)}"

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
