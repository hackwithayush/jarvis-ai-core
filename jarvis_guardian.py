"""
Jarvis v16.0 — 24/7 Autonomous Multi-Node Guardian & Watchdog Supervisor
Monitors, supervises, and maintains continuous 24/7 operation of:
  - Node A: JARVIS Web Gateway (app.py)
  - Node B: JARVIS Telegram Agent (telegram_bot.py)

Features:
  - Concurrent process supervision with independent crash isolation
  - Instant automatic restart upon failure or crash
  - Port 5000 auto-recovery & conflict resolution
  - Real-time Gmail alerting on crash loops
  - Live console streaming with colored node tagging
  - Clean graceful shutdown handling (Ctrl+C)
"""
import subprocess
import sys
import time
import os
import signal
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Set up main guardian logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | GUARDIAN | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "guardian_24_7.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("jarvis.guardian_24_7")

# Ensure UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class ProcessSupervisor:
    """Supervises an individual process node with auto-restart, logging, and crash tracking."""

    def __init__(self, name: str, script_name: str, log_filename: str):
        self.name = name
        self.script_path = os.path.join(BASE_DIR, script_name)
        self.log_path = os.path.join(LOG_DIR, log_filename)
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.crash_history = []
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the supervisor thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name=f"Supervisor-{self.name}")
        self.thread.start()

    def stop(self):
        """Stops supervision and terminates child process."""
        self.running = False
        with self.lock:
            if self.process and self.process.poll() is None:
                logger.info(f"Terminating {self.name} (PID: {self.process.pid})...")
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception:
                        pass

    def _free_port_if_needed(self):
        """Frees gateway port if this is the Web node and port is occupied."""
        if self.name.lower() == "web":
            try:
                target_port = int(os.environ.get("PORT", 5000))
                import psutil
                for conn in psutil.net_connections(kind='inet'):
                    if conn.laddr and conn.laddr.port == target_port:
                        if conn.pid and conn.pid != os.getpid():
                            logger.warning(f"Port {target_port} occupied by PID {conn.pid}. Clearing stale listener...")
                            try:
                                proc = psutil.Process(conn.pid)
                                proc.terminate()
                                proc.wait(timeout=2)
                            except Exception:
                                pass
            except Exception:
                pass

    def _stream_output(self, stream, prefix: str, log_file):
        """Streams process output to console and dedicated log file."""
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                clean_line = line.strip()
                if clean_line:
                    # Write to dedicated log
                    log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] {clean_line}\n")
                    log_file.flush()
                    # Print to console with prefix
                    print(f"[{prefix}] {clean_line}")
        except Exception:
            pass
        finally:
            stream.close()

    def _notify_crash_loop(self, recent_count: int, last_trace: str):
        """Sends a high-priority Gmail alert if a node gets stuck in a crash loop."""
        try:
            from core.gmail_manager import gmail_manager
            subject = f"⚠️ [JARVIS WATCHDOG ALERT] Node '{self.name}' Crash Loop ({recent_count} crashes)"
            body_text = f"""
================================================================================
⚠️ JARVIS 24/7 GUARDIAN WATCHDOG ALERT
================================================================================
Node: {self.name}
Script: {self.script_path}
Crashes in last 5 minutes: {recent_count}

LAST OBSERVED TRACEBACK / ERROR:
{last_trace}

ACTION TAKEN:
Guardian is maintaining continuous auto-recovery attempts with backoff.
================================================================================
"""
            gmail_manager.send_email(
                subject=subject,
                body_text=body_text,
                metadata={"node": self.name, "crashes": recent_count, "type": "watchdog_alert"}
            )
            logger.info(f"[WATCHDOG] Dispatched crash alert for {self.name} to Gmail.")
        except Exception as e:
            logger.error(f"[WATCHDOG] Failed to send crash notification: {e}")

    def _run_loop(self):
        """Continuous execution loop with crash recovery."""
        backoff_seconds = 2

        while self.running:
            self._free_port_if_needed()
            logger.info(f"🚀 Initializing {self.name} Node ({os.path.basename(self.script_path)})...")

            try:
                # Open dedicated log file for this run
                with open(self.log_path, "a", encoding="utf-8") as node_log:
                    node_log.write(f"\n--- SESSION STARTED AT {datetime.now()} ---\n")
                    node_log.flush()

                    env = os.environ.copy()
                    env["PYTHONUNBUFFERED"] = "1"

                    self.process = subprocess.Popen(
                        [sys.executable, "-u", self.script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        cwd=BASE_DIR,
                        env=env
                    )

                    logger.info(f"✅ {self.name} Online (PID: {self.process.pid})")

                    # Launch stdout and stderr reader threads
                    t_stdout = threading.Thread(
                        target=self._stream_output,
                        args=(self.process.stdout, self.name.upper(), node_log),
                        daemon=True
                    )
                    t_stderr = threading.Thread(
                        target=self._stream_output,
                        args=(self.process.stderr, f"{self.name.upper()} ERR", node_log),
                        daemon=True
                    )
                    t_stdout.start()
                    t_stderr.start()

                    # Wait for process exit
                    exit_code = self.process.wait()
                    t_stdout.join(timeout=1)
                    t_stderr.join(timeout=1)

                    if not self.running:
                        break

                    # Process died unexpectedly
                    now = time.time()
                    self.crash_history.append(now)
                    # Keep only last 5 minutes of crashes
                    self.crash_history = [t for t in self.crash_history if now - t <= 300]
                    recent_crashes = len(self.crash_history)

                    logger.error(f"❌ {self.name} Node terminated with Exit Code {exit_code}! (Crash count in 5m: {recent_crashes})")

                    # Check for crash loop threshold
                    if recent_crashes >= 3:
                        logger.critical(f"⚠️ {self.name} has crashed {recent_crashes} times recently!")
                        self._notify_crash_loop(recent_crashes, f"Process exited with code {exit_code}")
                        backoff_seconds = min(backoff_seconds * 2, 20)
                    else:
                        backoff_seconds = 3

            except Exception as e:
                logger.error(f"Failed to launch {self.name}: {e}")
                backoff_seconds = 5

            if self.running:
                logger.warning(f"🔄 Auto-Healing: Restarting {self.name} Node in {backoff_seconds}s...")
                time.sleep(backoff_seconds)

class Jarvis247Guardian:
    """Master 24/7 Orchestrator for JARVIS Web Gateway and Telegram Agent."""

    def __init__(self):
        self.web_supervisor = ProcessSupervisor(
            name="Web",
            script_name="app.py",
            log_filename="web_node.log"
        )
        self.telegram_supervisor = ProcessSupervisor(
            name="Telegram",
            script_name="telegram_bot.py",
            log_filename="telegram_node.log"
        )
        self.running = False

    def start(self):
        """Starts 24/7 supervision of both nodes."""
        self.running = True
        logger.info("=" * 65)
        logger.info("🛡️ JARVIS 24/7 AUTONOMOUS GUARDIAN ONLINE")
        logger.info("   Supervising: Web Interface (Port 5000) & Telegram Agent")
        logger.info("   Press Ctrl+C to gracefully stop all nodes.")
        logger.info("=" * 65)

        # Start nodes
        self.web_supervisor.start()
        time.sleep(2)  # Stagger initial boot
        self.telegram_supervisor.start()

        # Handle termination signals
        def _signal_handler(sig, frame):
            logger.info("\nReceived shutdown signal. Powering down 24/7 Guardian...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        # Health probe loop
        try:
            while self.running:
                time.sleep(30)
                # Periodic health verification
                web_alive = self.web_supervisor.process and self.web_supervisor.process.poll() is None
                tg_alive = self.telegram_supervisor.process and self.telegram_supervisor.process.poll() is None
                logger.info(f"💓 24/7 Health Check: Web Node={'ONLINE' if web_alive else 'RECOVERING'} | Telegram Node={'ONLINE' if tg_alive else 'RECOVERING'}")
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Gracefully stops both nodes."""
        self.running = False
        logger.info("Halting all child nodes...")
        self.web_supervisor.stop()
        self.telegram_supervisor.stop()
        logger.info("All JARVIS 24/7 nodes stopped successfully.")

if __name__ == "__main__":
    guardian = Jarvis247Guardian()
    guardian.start()
