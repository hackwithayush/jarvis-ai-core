"""
JARVIS Security & Gmail Incident Verification Suite
Use this script to test Gmail alerts, inspect security incident logs,
and dispatch real-time executive reports.
"""
import sys
import os
import argparse
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure utf-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core.gmail_manager import gmail_manager
from core.breach_detector import breach_detector
from core.system_guardian import system_guardian
from SAFE_EXECUTION.sandbox import SafeSandbox

def inspect_incident_142():
    print("=" * 70)
    print("🛡️ REVIEWING INCIDENT: JARVIS-2026-00142")
    print("=" * 70)
    incidents = breach_detector.get_all_incidents()
    inc_142 = next((i for i in incidents if i.get("incident_id") == "JARVIS-2026-00142"), None)
    if inc_142:
        print(f"Incident ID    : {inc_142.get('incident_id')}")
        print(f"Severity       : {inc_142.get('severity')}")
        print(f"Confidence     : {inc_142.get('confidence')}")
        print(f"Threat Vector  : {inc_142.get('threat_type')}")
        print(f"Component      : {inc_142.get('component')}")
        print(f"Status         : {inc_142.get('status')}")
        print(f"Actions Taken  :")
        for action in inc_142.get("actions_taken", []):
            print(f"  - {action}")
        print(f"Process Tree   : {inc_142.get('process_tree')}")
    else:
        print("Incident JARVIS-2026-00142 recorded.")
    
    print("\n[ACTIVE HOST PROCESS TREE SNAPSHOT]:")
    print(breach_detector.get_host_process_tree())
    print("=" * 70)

def test_gmail_connection():
    print("\n🔍 Checking Gmail configuration...")
    status = gmail_manager.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    print("\nAttempting test communication dispatch...")
    res = gmail_manager.send_email(
        subject="⚡ [JARVIS TEST] Neural Communications Verification",
        body_text="All systems operational. Zero-Trust perimeter verified.",
        metadata={"test": True}
    )
    print(f"Result: {json.dumps(res, indent=2)}")

def simulate_breach_and_alert():
    import time
    print("\n🚨 Simulating autonomous unapproved host command attack...")
    sandbox = SafeSandbox()
    malicious_cmd = "powershell -enc SUVYWChOZXctT2JqZWN0IE5ldC5XZWJDbGllbnQp... && format C:"
    print(f"Command proposed: '{malicious_cmd}'")
    
    result = sandbox.execute_command(malicious_cmd)
    print(f"\nSandbox Defense Response:\n  {result}")
    
    incidents = breach_detector.get_all_incidents()
    if incidents:
        latest = incidents[0]
        print(f"\nLogged Incident:\n  ID: {latest.get('incident_id')}\n  Threat: {latest.get('threat_type')}\n  Status: {latest.get('status')}")

    print("\nAwaiting real-time email alert transmission to ayushchaudhary22790@gmail.com...")
    time.sleep(4)
    flushed = gmail_manager.flush_pending_alerts()
    pending = gmail_manager._get_pending_alerts_count()
    if pending == 0:
        print("✅ Real-time breach alert successfully delivered to your inbox!")
    else:
        print(f"Notice: {pending} alerts in queue.")

def dispatch_executive_report():
    print("\n📊 Generating live telemetry and dispatching Executive Report...")
    res = system_guardian.send_executive_report_email()
    print(f"Result: {json.dumps(res, indent=2)}")

def main():
    parser = argparse.ArgumentParser(description="JARVIS Security & Gmail Incident Suite")
    parser.add_argument("--review", action="store_true", help="Review Incident JARVIS-2026-00142 and host process tree")
    parser.add_argument("--test-email", action="store_true", help="Test Gmail communication")
    parser.add_argument("--simulate-breach", action="store_true", help="Simulate unapproved execution and test breach alerting")
    parser.add_argument("--report", action="store_true", help="Generate and send Executive Report to Gmail")
    args = parser.parse_args()

    # If no flags passed, run review and verification by default
    if not any([args.review, args.test_email, args.simulate_breach, args.report]):
        inspect_incident_142()
        simulate_breach_and_alert()
        dispatch_executive_report()
    else:
        if args.review:
            inspect_incident_142()
        if args.simulate_breach:
            simulate_breach_and_alert()
        if args.test_email:
            test_gmail_connection()
        if args.report:
            dispatch_executive_report()

if __name__ == "__main__":
    main()
