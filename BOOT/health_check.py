"""
Health Monitor
Watches for stuck loops, memory leaks, and VRAM spikes in the background.
"""
import time
import psutil
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from LOGGING.logger import SystemLogger

class HealthMonitor:
    def __init__(self):
        self.running = True
        self.logger = SystemLogger()
        print("[HEALTH] Background Monitor active. Watching system stability.")
        
    def monitor(self):
        while self.running:
            time.sleep(30)
            
            # Check RAM Leak
            ram = psutil.virtual_memory().percent
            if ram > 92:
                msg = f"CRITICAL: System RAM approaching OOM threshold ({ram}%)."
                print(f"\n[HEALTH WARNING] {msg}")
                self.logger.log("metrics", msg)
                
            # Check CPU Spike (stuck loop detection)
            cpu = psutil.cpu_percent(interval=5)
            if cpu > 98:
                msg = f"CRITICAL: Sustained 98%+ CPU load! Possible infinite autonomous loop."
                print(f"\n[HEALTH WARNING] {msg}")
                self.logger.log("metrics", msg)
                
            # Check Disk
            disk = psutil.disk_usage('/').percent
            if disk > 98:
                print("\n[HEALTH WARNING] Critically low disk space! Disable file creation tools.")

if __name__ == "__main__":
    monitor = HealthMonitor()
    monitor.monitor()
