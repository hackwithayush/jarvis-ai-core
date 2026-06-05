"""
Observability Engine
Handles file-based logging for autonomous operations to prevent silent failures.
"""
import os
import time

class SystemLogger:
    def __init__(self):
        self.log_dir = os.path.join(os.path.dirname(__file__), "logs")
        self.categories = ["planner", "execution", "voice", "crash", "metrics"]
        
        # Ensure directory structure exists
        for cat in self.categories:
            os.makedirs(os.path.join(self.log_dir, cat), exist_ok=True)
            
        print("[OBSERVABILITY] Logging engine mounted. Listening for telemetry.")
            
    def log(self, category: str, message: str):
        """ Writes a timestamped log to the designated category file. """
        if category not in self.categories:
            category = "crash"
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        date_str = time.strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, category, f"{date_str}.log")
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"[LOGGER ERROR] Failed to write to {log_file}: {e}")
