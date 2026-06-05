"""
GPU/RAM Resource Governor
Monitors and manages VRAM usage, unloads inactive local models to prevent OOM.
"""
import requests
import psutil

class VRAMManager:
    def __init__(self):
        self.ollama_host = "http://127.0.0.1:11434"
        print("[GOVERNOR] Resource management engine online.")
        
    def check_system_resources(self) -> bool:
        """ Returns False if system RAM is critically low (>90%). """
        ram = psutil.virtual_memory().percent
        if ram > 90:
            print(f"[GOVERNOR] CRITICAL RAM WARNING: {ram}%. Throttling AI execution.")
            return False
        return True
        
    def unload_inactive_models(self):
        """ Forces Ollama to unload inactive models from the RTX 4060 VRAM. """
        print("[GOVERNOR] Sweeping VRAM... Unloading inactive Ollama models.")
        try:
            # Sending keep_alive=0 to ollama unloads the model immediately
            url = f"{self.ollama_host}/api/generate"
            
            models = ["deepseek-r1:7b", "qwen2.5-coder:7b", "llama3.1:8b"]
            for model in models:
                payload = {"model": model, "keep_alive": 0}
                requests.post(url, json=payload, timeout=5)
                
            print("[GOVERNOR] VRAM Sweep Complete. Memory cleared.")
        except Exception as e:
            print(f"[GOVERNOR ERROR] Could not connect to daemon to sweep VRAM: {e}")
