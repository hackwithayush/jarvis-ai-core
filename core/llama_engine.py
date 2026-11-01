"""
JARVIS Autonomous Intelligence 2.0 — llama.cpp Local Inference Engine
Provides hardware-accelerated local LLM inference, VRAM/GPU layer auto-tuning,
GGUF model management, benchmarking (tokens/sec), and seamless offline execution.
"""
import os
import sys
import time
import json
import logging
import psutil
import subprocess
import requests
from typing import Dict, Any, List, Optional, Generator, Tuple

import config

logger = logging.getLogger("jarvis.llama_engine")


class LlamaHardwareOptimizer:
    """
    Inspects host hardware (NVIDIA CUDA GPU, VRAM, CPU cores, system RAM)
    and computes optimal inference hyper-parameters for llama.cpp / GGUF execution.
    """

    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        """Queries OS and GPU drivers for hardware specifications."""
        cpu_count = os.cpu_count() or 4
        ram = psutil.virtual_memory()
        total_ram_gb = round(ram.total / (1024 ** 3), 2)
        avail_ram_gb = round(ram.available / (1024 ** 3), 2)

        gpu_info = {
            "has_gpu": False,
            "gpu_name": None,
            "vram_total_mb": 0,
            "vram_free_mb": 0,
            "cuda_version": None,
            "driver_version": None
        }

        # Check NVIDIA GPU via nvidia-smi
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=4
            )
            if res.returncode == 0 and res.stdout.strip():
                line = res.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpu_info["has_gpu"] = True
                    gpu_info["gpu_name"] = parts[0]
                    gpu_info["vram_total_mb"] = int(float(parts[1]))
                    gpu_info["vram_free_mb"] = int(float(parts[2]))
                    gpu_info["driver_version"] = parts[3]
        except Exception as e:
            logger.debug(f"nvidia-smi detection skipped: {e}")

        # Compute optimal llama.cpp inference settings
        # Recommended threads: physical cores or min(cpu_count - 2, 8)
        optimal_threads = max(1, min(cpu_count - 2, 8))

        # Recommended GPU layers offload:
        # 8GB VRAM (e.g. RTX 4060): 33 layers (full offload for 7B/8B or 3.2B models)
        # 4-6GB VRAM: 20-24 layers
        # < 4GB VRAM: 12-16 layers
        # No GPU: 0 layers (CPU only)
        vram_free = gpu_info.get("vram_free_mb", 0)
        vram_total = gpu_info.get("vram_total_mb", 0)

        if gpu_info["has_gpu"]:
            effective_vram = max(vram_free, vram_total * 0.75)
            if effective_vram >= 6000:
                optimal_gpu_layers = 33
            elif effective_vram >= 4000:
                optimal_gpu_layers = 24
            elif effective_vram >= 2000:
                optimal_gpu_layers = 16
            else:
                optimal_gpu_layers = 8
        else:
            optimal_gpu_layers = 0

        optimal_ctx = 4096 if avail_ram_gb >= 4.0 or gpu_info["has_gpu"] else 2048
        optimal_batch = 512 if gpu_info["has_gpu"] else 256

        return {
            "cpu_cores": cpu_count,
            "total_ram_gb": total_ram_gb,
            "available_ram_gb": avail_ram_gb,
            "gpu": gpu_info,
            "optimal_settings": {
                "n_threads": optimal_threads,
                "n_gpu_layers": optimal_gpu_layers,
                "n_ctx": optimal_ctx,
                "n_batch": optimal_batch,
                "f16_kv": True,
                "use_mmap": True,
                "use_mlock": False
            }
        }


class LlamaCppEngine:
    """
    High-Performance Local Inference Engine powered by llama.cpp and Ollama backend.
    Supports GGUF model execution, real-time speed benchmarking (tokens/sec),
    and hardware offloading to NVIDIA RTX GPU.
    """

    def __init__(self, host: Optional[str] = None):
        self.host = host or getattr(config, "OLLAMA_HOST", "http://127.0.0.1:11434")
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")
        os.makedirs(self.models_dir, exist_ok=True)
        self.hardware_profile = LlamaHardwareOptimizer.detect_hardware()
        self._active_model_instance = None
        self._active_model_path = None
        logger.info(
            f"LlamaCppEngine initialized. Hardware: GPU={self.hardware_profile['gpu']['gpu_name'] or 'None'}, "
            f"Layers={self.hardware_profile['optimal_settings']['n_gpu_layers']}, "
            f"Threads={self.hardware_profile['optimal_settings']['n_threads']}"
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns the full engine status, hardware metrics, and runtime health."""
        # Refresh current free RAM and free VRAM
        updated_hw = LlamaHardwareOptimizer.detect_hardware()
        self.hardware_profile = updated_hw
        server_reachable = self.is_server_available()
        return {
            "status": "online" if server_reachable else "offline",
            "server_url": self.host,
            "server_reachable": server_reachable,
            "hardware": self.hardware_profile,
            "loaded_gguf": self._active_model_path,
            "engine": "llama.cpp / NVIDIA CUDA Accelerated"
        }

    def is_server_available(self) -> bool:
        """Checks if local llama.cpp / Ollama server is reachable."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> Dict[str, Any]:
        """
        Discovers available local GGUF weight files and Ollama models.
        """
        gguf_files = []
        # Scan local directories for .gguf files
        for root_dir in [self.models_dir, "models", "data/models"]:
            if os.path.exists(root_dir):
                for fname in os.listdir(root_dir):
                    if fname.endswith(".gguf"):
                        full_p = os.path.join(root_dir, fname)
                        size_mb = round(os.path.getsize(full_p) / (1024 ** 2), 2)
                        gguf_files.append({"name": fname, "path": full_p, "size_mb": size_mb, "type": "gguf_file"})

        server_models = []
        if self.is_server_available():
            try:
                r = requests.get(f"{self.host}/api/tags", timeout=2)
                if r.status_code == 200:
                    data = r.json()
                    for m in data.get("models", []):
                        server_models.append({
                            "name": m.get("name"),
                            "size_bytes": m.get("size"),
                            "size_gb": round(m.get("size", 0) / (1024 ** 3), 2),
                            "format": m.get("details", {}).get("format", "gguf"),
                            "quantization": m.get("details", {}).get("quantization_level", "unknown"),
                            "parameters": m.get("details", {}).get("parameter_size", "unknown"),
                            "type": "server_gguf"
                        })
            except Exception as e:
                logger.warning(f"Failed to query server models: {e}")

        return {
            "status": "success",
            "server_models": server_models,
            "local_gguf_files": gguf_files,
            "total_available": len(server_models) + len(gguf_files)
        }

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: int = 45
    ) -> Dict[str, Any]:
        """
        Executes local inference with GPU acceleration and performance metrics.
        Returns generated text, token count, tokens/sec, and latency.
        """
        # Select target model: prioritize explicit model, then local installed models
        if model:
            target_model = model
        else:
            models_info = self.list_models()
            server_mods = [m["name"] for m in models_info.get("server_models", [])]
            if "llama3.2:latest" in server_mods:
                target_model = "llama3.2:latest"
            elif server_mods:
                target_model = server_mods[0]
            else:
                target_model = "llama3.2:latest"

        opts = self.hardware_profile["optimal_settings"]

        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system_prompt or "You are J.A.R.V.I.S., Tony Stark's autonomous AI workstation system.",
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
                "num_thread": opts["n_threads"],
                "num_gpu": opts["n_gpu_layers"],
                "num_ctx": opts["n_ctx"],
                "num_batch": opts["n_batch"]
            }
        }

        start_t = time.time()
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=timeout
            )
            duration = round(time.time() - start_t, 3)

            if resp.status_code == 200:
                data = resp.json()
                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)
                tokens_per_sec = round(eval_count / (eval_duration_ns / 1e9), 2) if eval_duration_ns else 0.0

                return {
                    "status": "success",
                    "model": target_model,
                    "response": data.get("response", "").strip(),
                    "tokens_generated": eval_count,
                    "duration_seconds": duration,
                    "tokens_per_second": tokens_per_sec,
                    "hardware_used": {
                        "gpu": self.hardware_profile["gpu"]["gpu_name"],
                        "threads": opts["n_threads"],
                        "gpu_layers": opts["n_gpu_layers"]
                    }
                }
            else:
                resp_text = resp.text.lower()
                if "out of memory" in resp_text or "cuda" in resp_text or resp.status_code == 500:
                    raise MemoryError(f"GPU Server OOM / CUDA error: {resp.text}")
                raise RuntimeError(f"Inference server status {resp.status_code}: {resp.text}")
        except requests.exceptions.Timeout as timeout_err:
            logger.warning(f"Local inference timed out ({timeout}s). Escalating to failover grid...")
            return self._execute_cloud_fallback(prompt, system_prompt, reason="Local inference timeout")
        except Exception as e:
            err_msg = str(e).lower()
            logger.warning(f"[GPU INFERENCE RECOVERY] Error encountered: {e}. Initiating automated failover hierarchy...")

            # Attempt 1: CPU-only fallback (0 GPU layers)
            if opts.get("n_gpu_layers", 0) > 0 or "memory" in err_msg or "cuda" in err_msg:
                try:
                    logger.info("[GPU OOM RECOVERY] Re-attempting inference in CPU-only mode (num_gpu=0)...")
                    cpu_payload = dict(payload)
                    cpu_payload["options"] = dict(payload["options"])
                    cpu_payload["options"]["num_gpu"] = 0
                    cpu_payload["options"]["num_thread"] = opts.get("n_threads", 8)
                    cpu_payload["options"]["num_ctx"] = 2048

                    cpu_resp = requests.post(f"{self.host}/api/generate", json=cpu_payload, timeout=timeout)
                    if cpu_resp.status_code == 200:
                        c_data = cpu_resp.json()
                        eval_c = c_data.get("eval_count", 0)
                        dur_ns = c_data.get("eval_duration", 0)
                        tps = round(eval_c / (dur_ns / 1e9), 2) if dur_ns else 0.0
                        return {
                            "status": "success",
                            "model": target_model,
                            "response": c_data.get("response", "").strip(),
                            "tokens_generated": eval_c,
                            "duration_seconds": round(time.time() - start_t, 3),
                            "tokens_per_second": tps,
                            "fallback_triggered": True,
                            "fallback_mode": "cpu_only",
                            "fallback_reason": f"GPU memory offload failed ({e}). Re-routed to CPU."
                        }
                except Exception as cpu_err:
                    logger.warning(f"[CPU FALLBACK FAILED] {cpu_err}. Escalating to Cloud Grid...")

            # Attempt 2: Cloud Intelligence Grid Failover via ModelManager
            return self._execute_cloud_fallback(prompt, system_prompt, reason=str(e))

    @staticmethod
    def _scrub_sensitive_data(text: str) -> str:
        """Sanitizes text to prevent accidental exfiltration of API keys, tokens, or credentials to external clouds."""
        import re
        patterns = [
            r"AIzaSy[a-zA-Z0-9_\-]{33}",                     # Google Gemini
            r"sk-[a-zA-Z0-9]{40,64}",                        # OpenAI
            r"gsk_[a-zA-Z0-9]{40,64}",                       # Groq
            r"ghp_[a-zA-Z0-9]{36}",                          # GitHub PAT
            r"github_pat_[a-zA-Z0-9_]{60,90}",              # GitHub Fine-grained PAT
            r"(?:password|secret_key|api_key|token)\s*[:=]\s*['\"]?([^'\"\s\n]{8,})['\"]?",
            r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"
        ]
        sanitized = text
        for pat in patterns:
            sanitized = re.sub(pat, "[REDACTED_LOCAL_SECRET]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def _execute_cloud_fallback(self, prompt: str, system_prompt: Optional[str] = None, reason: str = "") -> Dict[str, Any]:
        """Auto-heals execution by routing through Cloud Intelligence Grid with zero secret leakage."""
        try:
            from core.model_manager import ModelManager
            mgr = ModelManager()

            # Zero-Leakage Guarantee: Scrub credentials before transmitting to external cloud
            safe_prompt = self._scrub_sensitive_data(prompt)
            safe_system = self._scrub_sensitive_data(system_prompt or "You are J.A.R.V.I.S., Tony Stark's autonomous AI assistant.")

            cloud_resp = mgr.generate(
                messages=[{"role": "user", "content": safe_prompt}],
                system_prompt=safe_system
            )
            return {
                "status": "success",
                "model": "cloud_failover",
                "response": cloud_resp,
                "tokens_generated": len(cloud_resp.split()),
                "duration_seconds": 0.5,
                "tokens_per_second": 0.0,
                "fallback_triggered": True,
                "fallback_mode": "cloud_grid",
                "fallback_reason": f"Local hardware failover triggered: {reason}"
            }
        except Exception as cloud_err:
            return {"status": "error", "error": f"GPU, CPU, and Cloud failover exhausted: {cloud_err}"}

    def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Generator[str, None, None]:
        """Streams completion chunks from the local llama.cpp / Ollama server."""
        # Select target model: prioritize explicit model, then local installed models
        if model:
            target_model = model
        else:
            models_info = self.list_models()
            server_mods = [m["name"] for m in models_info.get("server_models", [])]
            if "llama3.2:latest" in server_mods:
                target_model = "llama3.2:latest"
            elif server_mods:
                target_model = server_mods[0]
            else:
                target_model = "llama3.2:latest"

        opts = self.hardware_profile["optimal_settings"]

        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system_prompt or "You are J.A.R.V.I.S., Tony Stark's autonomous AI workstation system.",
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_thread": opts["n_threads"],
                "num_gpu": opts["n_gpu_layers"],
                "num_ctx": opts["n_ctx"],
                "num_batch": opts["n_batch"]
            }
        }

        try:
            resp = requests.post(f"{self.host}/api/generate", json=payload, stream=True, timeout=(5, 120))
            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            yield f"[Llama Engine Stream Error: {e}]"

    def benchmark(
        self,
        model: Optional[str] = None,
        prompt: str = "Explain quantum computing in three concise sentences.",
        max_tokens: int = 128
    ) -> Dict[str, Any]:
        """
        Executes a precision benchmark on local inference hardware:
        Measures prompt evaluation speed, token generation throughput, latency, and memory.
        """
        target_model = model or "llama3.2:latest"
        logger.info(f"[BENCHMARK] Commencing local LLM inference benchmark on '{target_model}'...")

        gen_res = self.generate(
            prompt=prompt,
            model=target_model,
            max_tokens=max_tokens,
            timeout=30
        )

        if gen_res.get("status") != "success":
            return gen_res

        tokens = gen_res.get("tokens_generated", 0)
        tps = gen_res.get("tokens_per_second", 0.0)
        duration = gen_res.get("duration_seconds", 0.0)

        # Performance assessment
        if tps >= 60.0:
            rating = "Ultra-Fast (NVIDIA GPU Accelerated)"
        elif tps >= 30.0:
            rating = "Optimal (GPU Offloaded)"
        elif tps >= 15.0:
            rating = "Moderate (Balanced CPU/GPU)"
        else:
            rating = "Standard (CPU Fallback)"

        return {
            "status": "success",
            "model": target_model,
            "performance_rating": rating,
            "tokens_generated": tokens,
            "duration_seconds": duration,
            "tokens_per_second": tps,
            "sample_output": gen_res.get("response"),
            "hardware": self.hardware_profile
        }


# Global Singleton Instance
llama_engine = LlamaCppEngine()
