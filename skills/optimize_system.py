"""
Jarvis Skill — Optimize System (optimize_system)
A composite skill that checks live host health telemetry, requests capability authorization,
and runs safe self-healing purges on system temporary storage and DNS resolver caches.
"""
from core.system_guardian import system_guardian

MANIFEST = {
    "skill_id": "optimize_system",
    "name": "System Optimization Behavior",
    "description": "Composite orchestration skill that analyses telemetry load and runs automated temporary folder storage purges and network cache flushes.",
    "required_clearance": "HIGH",
    "required_capabilities": [
        "telemetry.query",
        "filesystem.write"
    ],
    "parameters": {
        "deep_clean": {
            "type": "boolean",
            "description": "If true, enforces structural environment PATH directory pruning.",
            "required": False
        }
    }
}

def execute(args: dict, clearance_tokens: dict) -> dict:
    """Executes composite telemetry analysis and workstation repair."""
    import psutil
    import time
    
    # 1. Inspect live system status
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    
    # 2. Extract authorization tokens issued by policy gating
    fs_token = clearance_tokens.get("filesystem.write")
    if not fs_token:
        raise PermissionError("Missing required filesystem.write clearance token to run optimization.")

    # 3. Call core system_guardian scans
    sec = system_guardian.audit_security_status()
    bugs = system_guardian.audit_system_bugs()
    health_before = system_guardian.compute_health_score(sec, bugs) * 10.0
    
    # 4. Trigger resolve with approved actions
    approved = ["temp_cleanup", "dns_flush"]
    if args.get("deep_clean", False):
        approved.append("prune_path")
        
    repair_report = system_guardian.resolve_threats_and_bugs(
        scan_results={"security": sec, "bugs": bugs},
        risk_policy="HIGH",
        approved_actions=approved
    )
    
    # 5. Audit post-repair status
    time.sleep(0.5)
    post_sec = system_guardian.audit_security_status()
    post_bugs = system_guardian.audit_system_bugs()
    health_after = system_guardian.compute_health_score(post_sec, post_bugs) * 10.0
    
    return {
        "status": "COMPLETED",
        "baseline_telemetry": {
            "cpu_percent": f"{cpu}%",
            "ram_percent": f"{mem}%"
        },
        "health_restoration": {
            "before": f"{health_before}/100.0",
            "after": f"{health_after}/100.0",
            "restored_delta": f"+{health_after - health_before:.1f}"
        },
        "actions_taken": repair_report.get("actions", []),
        "errors": repair_report.get("errors", [])
    }
