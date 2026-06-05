import subprocess
import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def launch_jarvis():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        app_script = os.path.join(base_dir, "app.py")

        print("🚀 Starting JARVIS Neural System...")

        process = subprocess.Popen(
            [sys.executable, app_script],
            cwd=base_dir
        )

        print(f"✅ JARVIS launched (PID: {process.pid})")

    except Exception as e:
        print(f"❌ Error launching JARVIS: {e}")

if __name__ == "__main__":
    launch_jarvis()
