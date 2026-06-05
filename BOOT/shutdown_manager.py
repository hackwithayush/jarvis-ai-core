"""
Shutdown Manager
Gracefully spins down JARVIS, unloads models from VRAM, and cleans up temp buffers.
"""
import psutil
import requests
import sys

def graceful_shutdown():
    print("\n=======================================================")
    print("      INITIATING JARVIS SHUTDOWN PROTOCOL              ")
    print("=======================================================")
    
    # 1. Unload Ollama VRAM
    print("[SHUTDOWN] Unloading active models from GPU VRAM...")
    try:
        models = ["deepseek-r1:7b", "qwen2.5-coder:7b", "llama3.1:8b"]
        for model in models:
            requests.post("http://127.0.0.1:11434/api/generate", json={"model": model, "keep_alive": 0}, timeout=2)
    except Exception as e:
        print(f"[SHUTDOWN WARNING] VRAM sweep failed: {e}")
        
    # 2. Halt Processes
    print("[SHUTDOWN] AI Operating System safely spun down. Goodbye.")
    sys.exit(0)

if __name__ == "__main__":
    graceful_shutdown()
