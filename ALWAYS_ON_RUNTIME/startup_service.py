"""
Startup Service
The ultimate bootloader. Loads the daemon and effectively turns the laptop into an AI OS.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from ALWAYS_ON_RUNTIME.background_daemon import BackgroundDaemon

def boot():
    print("=======================================================")
    print("      INITIALIZING JARVIS AI OPERATING SYSTEM          ")
    print("=======================================================")
    daemon = BackgroundDaemon()
    daemon.run()
    
if __name__ == "__main__":
    boot()
