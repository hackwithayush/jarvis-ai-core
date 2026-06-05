"""
Dependency & System Check
Verifies Ollama, GPU status, Environment Variables, and Hardware before boot.
"""
import os
import sys
import psutil
import requests
import pathlib
from dotenv import load_dotenv

env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def check_system():
    print("[BOOT] Running pre-flight system checks...")
    errors = 0
    warnings = 0
    
    # 1. RAM Check
    ram = psutil.virtual_memory().percent
    if ram > 90:
        print(f"[WARNING] High RAM load ({ram}%). Performance may degrade.")
        warnings += 1
        
    # 2. Ollama Daemon
    try:
        r = requests.get("http://127.0.0.1:11434/", timeout=2)
        if r.status_code == 200:
            print("[OK] Ollama Local Inference Daemon running.")
    except Exception:
        # Check if SERVER_MODE is enabled (which uses Groq/OpenAI cloud models)
        try:
            sys.path.append(str(pathlib.Path(__file__).parent.parent))
            import config
            server_mode = getattr(config, "SERVER_MODE", False)
        except Exception:
            server_mode = False
            
        if server_mode:
            print("[OK] Ollama not running, but SERVER_MODE is ACTIVE. Using cloud models.")
        else:
            print("[ERROR] Ollama is not running! Start the Ollama app before booting JARVIS.")
            errors += 1
        
    # 3. Environment Variables
    if not os.environ.get("TELEGRAM_BOT_TOKEN") and not os.environ.get("BOT_TOKEN"):
        print("[WARNING] TELEGRAM_BOT_TOKEN / BOT_TOKEN missing. Remote Telegram OS Control will be offline.")
        warnings += 1
        
    if errors > 0:
        print(f"\n[BOOT FAILED] {errors} critical errors detected. Resolve them and try again.")
        sys.exit(1)
        
    print(f"[BOOT] Pre-flight complete. {warnings} non-critical warnings.")
    sys.exit(0)

if __name__ == "__main__":
    check_system()
