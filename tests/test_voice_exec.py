import requests
import json
import time

test_commands = [
    "Jarvis can you open notepad",
    "take a screenshot",
    "what time is it",
    "how much battery is left",
    "check system status",
    "close notepad"
]

print("=== STARTING VOICE DIRECTIVE LIVE EXECUTION TESTS ===")
for cmd in test_commands:
    try:
        r = requests.post("http://127.0.0.1:5000/api/voice/command", json={"transcript": cmd}, timeout=5)
        data = r.json()
        print(f"COMMAND: {cmd}")
        print(f"  STATUS : {data.get('status')}")
        print(f"  ACTION : {data.get('action')}")
        print(f"  SPOKEN : {data.get('spoken_response')}")
        print("-" * 50)
        time.sleep(0.5)
    except Exception as e:
        print(f"FAILED on '{cmd}': {e}")
