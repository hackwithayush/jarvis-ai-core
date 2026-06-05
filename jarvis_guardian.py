import subprocess
import sys
import time
import os
import logging
from datetime import datetime

# ─── Configuration ──────────────────────────────────────────────
BOT_SCRIPT = "telegram_bot.py"
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | GUARDIAN | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "guardian.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("guardian")

def kill_zombies():
    """Kill all existing python processes to avoid port/token conflicts."""
    logger.info("Purging neural grid of zombie processes...")
    try:
        # We don't want to kill ourselves! 
        # But in a simple script, killing all other python processes is safest.
        # Use taskkill on Windows
        current_pid = os.getpid()
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], capture_output=True)
        # Note: This will kill the guardian too if run normally, but we call it at start.
    except Exception as e:
        logger.error(f"Failed to purge zombies: {e}")

def run_bot():
    """Run the bot and monitor for crashes."""
    while True:
        logger.info(f"Starting JARVIS Core ({BOT_SCRIPT})...")
        
        # Run bot as a subprocess
        process = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Monitor output in real-time
        try:
            while True:
                line = process.stdout.readline()
                if line:
                    print(f"[BOT] {line.strip()}")
                
                if process.poll() is not None:
                    # Bot has exited
                    stderr_output = process.stderr.read()
                    logger.error(f"JARVIS Core crashed!\nTraceback:\n{stderr_output}")
                    
                    # Log crash to a mission report
                    with open(os.path.join(LOG_DIR, "crash_report.log"), "a") as f:
                        f.write(f"\n--- CRASH AT {datetime.now()} ---\n{stderr_output}\n")
                    
                    break
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Guardian shutting down...")
            process.terminate()
            break
        except Exception as e:
            logger.error(f"Guardian error: {e}")
            process.terminate()
            
        logger.warning("Restarting mission in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    # We don't kill zombies here because it would kill the guardian itself.
    # The user should run this script from a clean environment.
    run_bot()
