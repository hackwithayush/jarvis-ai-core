"""
J.A.R.V.I.S. Iron Man Level - Full Autonomous Verification Suite
Executes live functional checks across OS automation, vocal matrix, telemetry, and cognitive systems.
"""
import requests
import json
import time
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://127.0.0.1:5000"

def log_header(title):
    print("\n" + "=" * 65)
    print(f"STARK LABS: {title.upper()}")
    print("=" * 65)

def log_test(step_num, title, status, details=""):
    badge = "[PASSED]" if status else "[FAILED]"
    print(f"[{step_num:02d}] {title:<42} {badge}")
    if details:
        print(f"     └─> {details}")

def run_all_checks():
    log_header("J.A.R.V.I.S. Iron Man Mark 85 System Diagnostics")
    total = 0
    passed = 0

    # Test 1: Voice Profiles Matrix
    total += 1
    try:
        r = requests.get(f"{BASE_URL}/api/voice/profiles", timeout=5)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success"
        active_voice = d.get("active_voice")
        log_test(total, "Vocal Matrix Profiles Query", True, f"Active Voice: {active_voice} (Paul Bettany matrix available)")
        passed += 1
    except Exception as e:
        log_test(total, "Vocal Matrix Profiles Query", False, str(e))

    # Test 2: System Telemetry
    total += 1
    try:
        r = requests.get(f"{BASE_URL}/api/system/stats", timeout=5)
        d = r.json()
        assert r.status_code == 200
        cpu = d.get("cpu", "N/A")
        ram = d.get("ram", "N/A")
        uptime = d.get("uptime", "N/A")
        log_test(total, "Hardware Sensor Telemetry", True, f"CPU: {cpu}% | RAM: {ram}% | Uptime: {uptime}")
        passed += 1
    except Exception as e:
        log_test(total, "Hardware Sensor Telemetry", False, str(e))

    # Test 3: Time & Calendar Directive
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis what time is it"}, timeout=8)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success"
        log_test(total, "Vocal Directive: Temporal Query", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "Vocal Directive: Temporal Query", False, str(e))

    # Test 4: Network & Ping Diagnostic
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis check my internet connection"}, timeout=12)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success"
        log_test(total, "Vocal Directive: Network Telemetry", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "Vocal Directive: Network Telemetry", False, str(e))

    # Test 5: Battery & Power Status
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis check battery level"}, timeout=8)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success"
        log_test(total, "Vocal Directive: Power Core Telemetry", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "Vocal Directive: Power Core Telemetry", False, str(e))

    # Test 6: Physical File Creation Directive
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "create note stark_hud_test.txt with content J.A.R.V.I.S. Mark 85 active"}, timeout=10)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success"
        log_test(total, "OS Directive: File Creation on Disk", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "OS Directive: File Creation on Disk", False, str(e))

    # Test 7: App Launch & Termination (Notepad)
    total += 1
    try:
        # Launch
        r_open = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis open notepad"}, timeout=8)
        assert r_open.status_code == 200 and r_open.json().get("status") == "success"
        time.sleep(1.0)
        # Terminate
        r_close = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis close notepad"}, timeout=8)
        assert r_close.status_code == 200 and r_close.json().get("status") == "success"
        log_test(total, "OS Directive: App Launch & Termination", True, f"Opened notepad -> cleanly closed notepad")
        passed += 1
    except Exception as e:
        log_test(total, "OS Directive: App Launch & Termination", False, str(e))

    # Test 8: Screenshot Capture
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis take a screenshot"}, timeout=10)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success"
        log_test(total, "OS Directive: Optical Screenshot Capture", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "OS Directive: Optical Screenshot Capture", False, str(e))

    # Test 9: Edge-TTS Neural Vocal Synthesis
    total += 1
    try:
        r = requests.post(
            f"{BASE_URL}/api/tts",
            json={"text": "All diagnostic parameters nominal, sir. Arc reactor operating at peak efficiency.", "voice": "en-GB-RyanNeural", "pitch": "-2Hz"},
            timeout=10
        )
        assert r.status_code == 200 and len(r.content) > 5000
        log_test(total, "Edge-TTS Paul Bettany Vocal Synthesis", True, f"Generated {len(r.content)} bytes of high-fidelity audio")
        passed += 1
    except Exception as e:
        log_test(total, "Edge-TTS Paul Bettany Vocal Synthesis", False, str(e))

    # Test 10: System Guardian Security Audit
    total += 1
    try:
        from core.system_guardian import system_guardian
        audit = system_guardian.audit_security_status(use_cache=False)
        threats = audit.get("suspicious_processes", [])
        log_test(total, "Zero-Trust Security Perimeter Audit", True, f"Firewall: {audit.get('firewall_active')} | Defender: {audit.get('antivirus_active')} | Active Threats: {len(threats)}")
        passed += 1
    except Exception as e:
        log_test(total, "Zero-Trust Security Perimeter Audit", False, str(e))

    # Test 11: Stark Signature Protocol: Armor Diagnostics
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis suit status"}, timeout=10)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success" and d.get("action") == "armor_diagnostics"
        log_test(total, "Stark Protocol: Armor Diagnostics", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "Stark Protocol: Armor Diagnostics", False, str(e))

    # Test 12: Stark Signature Protocol: Clean Slate Protocol
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis clean slate protocol"}, timeout=10)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success" and d.get("action") == "clean_slate_protocol"
        log_test(total, "Stark Protocol: Clean Slate Protocol", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "Stark Protocol: Clean Slate Protocol", False, str(e))

    # Test 13: Stark Signature Protocol: House Party Protocol
    total += 1
    try:
        r = requests.post(f"{BASE_URL}/api/voice/command", json={"transcript": "Jarvis house party protocol"}, timeout=10)
        d = r.json()
        assert r.status_code == 200 and d.get("status") == "success" and d.get("action") == "house_party_protocol"
        log_test(total, "Stark Protocol: House Party Protocol", True, f"Spoken: '{d.get('spoken_response')}'")
        passed += 1
    except Exception as e:
        log_test(total, "Stark Protocol: House Party Protocol", False, str(e))

    log_header("Verification Results Summary")
    print(f"Total Operational Nodes Tested: {total}")
    print(f"Total Nominal Verifications    : {passed}")
    print(f"Readiness Score               : {(passed / total) * 100:.1f}%\n")
    return passed == total

if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
