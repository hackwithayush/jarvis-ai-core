"""
Jarvis Skill — Secure Workstation (secure_workstation)
Runs security scans, assesses persistence threats, and enforces firewall checks.
"""
from core.system_guardian import system_guardian

MANIFEST = {
    "skill_id": "secure_workstation",
    "name": "Workstation Security Gating Behavior",
    "description": "Performs security audits, assesses active firewall rules, and detects suspicious registry items.",
    "required_clearance": "LOW",
    "required_capabilities": [
        "filesystem.read"
    ],
    "parameters": {
        "deep_audit": {
            "type": "boolean",
            "description": "If true, queries all persistence registry keys.",
            "required": False
        }
    }
}

def execute(args: dict, clearance_tokens: dict) -> dict:
    """Executes high-safety system security reviews."""
    sec = system_guardian.audit_security_status()
    
    warnings = sec.get("warnings", [])
    suspicious_startup = sec.get("suspicious_startup_keys", [])
    
    return {
        "status": "SECURED" if sec.get("status") == "SECURE" else "AUDITED",
        "defender_active": sec.get("defender_active"),
        "firewall_active": sec.get("firewall_active"),
        "protection_details": sec.get("protection_details"),
        "suspicious_startup_count": len(suspicious_startup),
        "threat_warnings": warnings
    }
