"""
Idle Monitor
A background thread that runs when JARVIS is IDLE, checking CPU/RAM and alerting if needed.
"""
import threading
import time
import psutil

class IdleMonitor(threading.Thread):
    def __init__(self, queue):
        super().__init__(daemon=True)
        self.queue = queue
        
    def run(self):
        while True:
            # Only monitor if JARVIS isn't busy executing a heavy AI task
            if self.queue.state.name == "IDLE":
                cpu = psutil.cpu_percent(interval=1)
                
                # Example threshold triggers
                if cpu > 95:
                    print("\n[MONITOR WARNING] High CPU Usage Detected (>95%)!")
                    # In future, this can trigger self.queue to auto-speak an alert
            time.sleep(15)
