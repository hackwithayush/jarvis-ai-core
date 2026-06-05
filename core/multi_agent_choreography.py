"""
Jarvis v15.0 — Multi-Agent Choreography & Real-Time Orchestration Layer
Ties Diagnostics, Correlation, Policy Enforcement, Remediation, and Rollback Supervisor into an asynchronous pub/sub pipeline.
"""
import os
import sys
import time
import logging
import hmac
import hashlib
import json
import uuid
import shutil
import platform
from typing import Dict, Any, List, Optional, Callable

from core.event_bus import event_bus
from core.system_guardian import system_guardian

logger = logging.getLogger("jarvis.multi_agent_choreography")

# Secure agent signature secret (fixed session key for HMAC verification)
HMAC_SECRET = b"jarvis_neural_os_agent_secure_token_key_2026"

def generate_cryptographic_token(action: str, validity_seconds: int = 60) -> dict:
    """Mints a secure HMAC-SHA256 authorization token signed by the Policy Agent."""
    nonce = str(uuid.uuid4())
    timestamp = time.time()
    payload = {
        "action": action,
        "nonce": nonce,
        "timestamp": timestamp,
        "expires": timestamp + validity_seconds
    }
    # Create deterministic signature
    serialized = json.dumps(payload, sort_keys=True)
    signature = hmac.new(HMAC_SECRET, serialized.encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        "payload": payload,
        "signature": signature
    }

def verify_cryptographic_token(action: str, token: dict) -> bool:
    """Cryptographically verifies that the token signature is valid and not expired."""
    try:
        payload = token.get("payload", {})
        signature = token.get("signature", "")
        
        # Verify action matches
        if payload.get("action") != action:
            logger.error(f"[TOKEN VERIFICATION] Action mismatch: expected '{action}', got '{payload.get('action')}'")
            return False
            
        # Verify expiration
        if time.time() > payload.get("expires", 0):
            logger.error("[TOKEN VERIFICATION] Cryptographic token has expired.")
            return False
            
        # Verify HMAC signature
        serialized = json.dumps(payload, sort_keys=True)
        expected_sig = hmac.new(HMAC_SECRET, serialized.encode('utf-8'), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected_sig, signature):
            logger.error("[TOKEN VERIFICATION] Cryptographic signature invalid! Tampering suspected.")
            return False
            
        return True
    except Exception as e:
        logger.error(f"[TOKEN VERIFICATION ERROR] Failed to verify token: {e}")
        return False


class DiagnosticsAgent:
    """Read-Only Observability Scanner."""
    def __init__(self):
        self.name = "DiagnosticsAgent"
        # Register to trigger topic
        event_bus.subscribe("diagnostics/trigger", self.on_trigger_scan)
        logger.info("[DIAGNOSTICS AGENT] Subscribed to 'diagnostics/trigger'")

    def on_trigger_scan(self, payload: Any = None):
        """Handler for diagnostic scan requests."""
        logger.info("[DIAGNOSTICS AGENT] Received scan trigger.")
        try:
            sec_scan = system_guardian.audit_security_status()
            bug_scan = system_guardian.audit_system_bugs()
            
            scan_results = {
                "timestamp": time.time(),
                "security": sec_scan,
                "bugs": bug_scan
            }
            logger.info("[DIAGNOSTICS AGENT] Scan completed. Publishing results.")
            event_bus.publish("diagnostics/scan_completed", scan_results)
        except Exception as e:
            logger.error(f"[DIAGNOSTICS AGENT ERROR] Scan failed: {e}")
            event_bus.publish("diagnostics/scan_failed", str(e))


class EventCorrelationEngineAgent:
    """Read-Only Threat and Log Analyst."""
    def __init__(self):
        self.name = "EventCorrelationEngineAgent"
        event_bus.subscribe("diagnostics/scan_completed", self.on_scan_completed)
        logger.info("[CORRELATION ENGINE AGENT] Subscribed to 'diagnostics/scan_completed'")

    def on_scan_completed(self, scan_results: dict):
        """Processes scan telemetry via sliding window Bayesian Root Cause Analysis."""
        logger.info("[CORRELATION ENGINE AGENT] Correlating diagnostic telemetry...")
        try:
            # Root Cause Engine is already integrated inside system_guardian.audit_system_bugs(), 
            # let's extract the RCA analysis block or calculate on-the-fly.
            bugs = scan_results.get("bugs", {})
            rca_report = bugs.get("root_cause_analysis", {})
            
            correlation_payload = {
                "scan_results": scan_results,
                "rca_report": rca_report,
                "root_cause_score": rca_report.get("root_cause_score", 0.0),
                "primary_vectors": rca_report.get("primary_vectors", []),
                "recommended_remediations": rca_report.get("recommended_remediations", []),
                "remediation_override": rca_report.get("remediation_override", False)
            }
            logger.info(f"[CORRELATION ENGINE AGENT] Analysis complete. Score: {correlation_payload['root_cause_score']}. Publishing...")
            event_bus.publish("correlation/analysis_completed", correlation_payload)
        except Exception as e:
            logger.error(f"[CORRELATION ENGINE AGENT ERROR] Correlation failed: {e}")


class PolicyEnforcementAgent:
    """Risk Gatekeeper and Approval Manager."""
    def __init__(self, risk_policy: str = "HIGH"):
        self.name = "PolicyEnforcementAgent"
        self.risk_policy = risk_policy.upper()
        # Risk map matching system_guardian risk thresholds
        self.risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        event_bus.subscribe("correlation/analysis_completed", self.on_analysis_completed)
        logger.info(f"[POLICY ENFORCEMENT AGENT] Subscribed to 'correlation/analysis_completed' (Policy: {self.risk_policy})")

    def set_policy(self, risk_policy: str):
        self.risk_policy = risk_policy.upper()
        logger.info(f"[POLICY ENFORCEMENT AGENT] Policy upgraded to: {self.risk_policy}")

    def on_analysis_completed(self, correlation_payload: dict):
        """Evaluates analyzed root causes against the active Risk policy matrix."""
        logger.info("[POLICY ENFORCEMENT AGENT] Evaluating threat vulnerabilities...")
        
        if correlation_payload.get("remediation_override", False):
            logger.warning("[POLICY ENFORCEMENT AGENT] Hardware Bus Failure detected. Remediation override active: Auto-fixes BLOCKED.")
            event_bus.publish("policy/override_active", {"reason": "Hardware instability detected. Manual engineering required."})
            return

        scan_results = correlation_payload.get("scan_results", {})
        bugs = scan_results.get("bugs", {})
        sec = scan_results.get("security", {})

        # List out required/detected actions
        detected_problems = []
        
        # 1. Bloat Cleanup (LOW risk)
        if bugs.get("bloat_size_mb", 0) > 100 or "bloat_cleanup" in correlation_payload.get("recommended_remediations", []):
            detected_problems.append(("clean_temp", "LOW"))
            
        # 2. DNS cache (LOW risk)
        if bugs.get("event_log_errors") or any("network" in str(e).lower() for e in bugs.get("warnings", [])):
            detected_problems.append(("flush_dns", "LOW"))
            
        # 3. Path repair (MEDIUM risk)
        if bugs.get("broken_env_paths"):
            detected_problems.append(("path_repair", "MEDIUM"))
            
        # 4. Hog process (HIGH risk)
        if bugs.get("resource_hogs"):
            detected_problems.append(("kill_process", "HIGH"))

        policy_val = self.risk_levels.get(self.risk_policy, 3)

        for action, severity in detected_problems:
            severity_val = self.risk_levels.get(severity, 1)
            
            # Authorize based on policy limits
            authorized = False
            pending_confirmation = False
            
            if policy_val == 4:  # CRITICAL/Simulation mode
                authorized = True # Sandbox simulator handles this
            elif severity_val <= policy_val:
                authorized = True
            else:
                pending_confirmation = True

            if authorized:
                token = generate_cryptographic_token(action)
                payload = {
                    "action": action,
                    "severity": severity,
                    "token": token,
                    "scan_context": scan_results,
                    "risk_policy": self.risk_policy
                }
                logger.info(f"[POLICY ENFORCEMENT AGENT] Action '{action}' AUTHORIZED. Cryptographic token generated.")
                event_bus.publish("policy/execution_authorized", payload)
            elif pending_confirmation:
                logger.warning(f"[POLICY ENFORCEMENT AGENT] Action '{action}' BLOCKED. Severity '{severity}' exceeds policy threshold '{self.risk_policy}'. Approval required.")
                event_bus.publish("policy/approval_required", {
                    "action": action,
                    "severity": severity,
                    "reason": f"Action exceeds current risk clearance level ({self.risk_policy})."
                })


class RemediationAgent:
    """Sandboxed & Live Execution Specialist."""
    def __init__(self):
        self.name = "RemediationAgent"
        self._rollback_snapshots = {}
        event_bus.subscribe("policy/execution_authorized", self.on_execution_authorized)
        event_bus.subscribe("remediation/rollback_trigger", self.on_rollback_trigger)
        logger.info("[REMEDIATION AGENT] Subscribed to execution & rollback triggers.")

    def on_execution_authorized(self, auth_payload: dict):
        """Verifies cryptographic token and executes authorized repairs under system baseline safeguards."""
        action = auth_payload.get("action")
        token = auth_payload.get("token")
        scan_context = auth_payload.get("scan_context", {})
        risk_policy = auth_payload.get("risk_policy", "HIGH")
        
        logger.info(f"[REMEDIATION AGENT] Received authorized request to perform '{action}'.")
        
        # 1. Cryptographically verify the Policy signature token
        if not verify_cryptographic_token(action, token):
            logger.critical(f"[REMEDIATION AGENT] Cryptographic handshake failed! Refusing execution for '{action}'.")
            event_bus.publish("remediation/execution_failed", {
                "action": action,
                "error": "Cryptographic authorization token validation failed."
            })
            return

        # 2. Capture baseline rollback snapshot before modifying files or registry environment paths
        if action == "path_repair":
            if platform.system().lower() == "windows":
                val = system_guardian._read_user_path()
                # Store rollback key
                snapshot_id = str(uuid.uuid4())
                self._rollback_snapshots[snapshot_id] = {"type": "path", "value": val}
                auth_payload["snapshot_id"] = snapshot_id
                logger.info(f"[REMEDIATION AGENT] Saved pre-repair PATH registry snapshot: ID={snapshot_id}")

        # 3. Execute the repair using SystemGuardian resolver
        try:
            logger.info(f"[REMEDIATION AGENT] Committing repair '{action}' to environment...")
            
            # Map single actions to the list expected by resolve_threats_and_bugs
            approved_actions_map = {
                "clean_temp": "clean_temp",
                "flush_dns": "flush_dns",
                "path_repair": "path_repair",
                "kill_process": "hog_termination"
            }
            mapped_action = approved_actions_map.get(action, action)
            
            result = system_guardian.resolve_threats_and_bugs(
                scan_results=scan_context,
                risk_policy=risk_policy,
                approved_actions=[mapped_action]
            )
            
            report = {
                "action": action,
                "success": result.get("success", False),
                "actions_taken": result.get("actions", []),
                "errors": result.get("errors", []),
                "telemetry": result.get("telemetry", {}),
                "auth_payload": auth_payload
            }
            
            logger.info(f"[REMEDIATION AGENT] Repair '{action}' complete. Publishing status.")
            event_bus.publish("remediation/execution_completed", report)
        except Exception as e:
            logger.error(f"[REMEDIATION AGENT ERROR] Execution failed for '{action}': {e}")
            event_bus.publish("remediation/execution_failed", {"action": action, "error": str(e)})

    def on_rollback_trigger(self, trigger_payload: dict):
        """Executes instant restore from recorded snapshot to restore system integrity."""
        snapshot_id = trigger_payload.get("snapshot_id")
        action = trigger_payload.get("action")
        
        logger.warning(f"[REMEDIATION AGENT] ROLLBACK TRIGGER RECEIVED. Reverting modifications for action '{action}'...")
        
        snapshot = self._rollback_snapshots.get(snapshot_id)
        if not snapshot:
            err_msg = f"Rollback snapshot ID '{snapshot_id}' not found."
            logger.error(f"[REMEDIATION AGENT ERROR] {err_msg}")
            event_bus.publish("remediation/rollback_failed", {"action": action, "error": err_msg})
            return

        try:
            if snapshot["type"] == "path":
                if platform.system().lower() == "windows":
                    logger.info("[REMEDIATION AGENT] Reverting HKCU Environment Path to baseline...")
                    system_guardian._write_user_path(snapshot["value"])
                    
                    # Re-broadcast environment change notification
                    try:
                        import ctypes
                        HWND_BROADCAST = 0xffff
                        WM_SETTINGCHANGE = 0x001a
                        ctypes.windll.user32.SendNotifyMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
                    except Exception as bx:
                        logger.warning(f"Failed to broadcast setting change: {bx}")
                        
                    logger.info(f"[REMEDIATION AGENT] Rollback successful. Restored PATH to: {snapshot['value']}")
                    event_bus.publish("remediation/rollback_completed", {
                        "action": action,
                        "snapshot_id": snapshot_id,
                        "success": True,
                        "restored_value": snapshot["value"]
                    })
                    # Clean up
                    del self._rollback_snapshots[snapshot_id]
                else:
                    raise OSError("Registry rollback is only supported on Windows.")
            else:
                raise ValueError(f"Unknown snapshot type '{snapshot['type']}'")
        except Exception as e:
            logger.error(f"[REMEDIATION AGENT ERROR] Rollback restore failed: {e}")
            event_bus.publish("remediation/rollback_failed", {"action": action, "error": str(e)})


class RollbackSupervisor:
    """Dynamic Stability Guardian & Dev Tool Circuit Breaker."""
    def __init__(self):
        self.name = "RollbackSupervisor"
        event_bus.subscribe("remediation/execution_completed", self.on_execution_completed)
        logger.info("[ROLLBACK SUPERVISOR] Subscribed to 'remediation/execution_completed'")

    def on_execution_completed(self, report: dict):
        """Verifies developer toolpath integrity and triggers auto-rollback on regressions."""
        action = report.get("action")
        auth_payload = report.get("auth_payload", {})
        snapshot_id = auth_payload.get("snapshot_id")
        
        logger.info(f"[ROLLBACK SUPERVISOR] Auditing workstation stability after '{action}'...")
        
        # 1. Dev runtime integrity check
        dev_tools = ["python", "git", "node", "code"]
        broken_tools = []
        
        # Simulate check
        for tool in dev_tools:
            try:
                # Use shutil.which to verify pathing
                found = shutil.which(tool)
                if not found:
                    broken_tools.append(tool)
            except Exception as e:
                logger.error(f"[ROLLBACK SUPERVISOR ERROR] Error locating '{tool}': {e}")
                broken_tools.append(tool)

        # 2. Trigger circuit breaker rollback if core developer toolpaths are broken
        if broken_tools and snapshot_id:
            logger.critical(f"[ROLLBACK SUPERVISOR CIRCUIT-BREAKER] Post-repair validation FAILED! Broken runtimes: {', '.join(broken_tools)}.")
            event_bus.publish("rollback/triggered", {
                "action": action,
                "broken_runtimes": broken_tools,
                "snapshot_id": snapshot_id
            })
            # Dispatch command to Remediation Agent to restore
            event_bus.publish("remediation/rollback_trigger", {
                "action": action,
                "snapshot_id": snapshot_id,
                "reason": f"Developer toolpaths broken: {', '.join(broken_tools)}"
            })
        else:
            logger.info(f"[ROLLBACK SUPERVISOR] Workstation stability verified. No runtime regressions detected.")
            event_bus.publish("rollback/stable", {
                "action": action,
                "verified_tools": [t for t in dev_tools if t not in broken_tools]
            })

# Instantiate agents programmatically to auto-listen once imported
diagnostics_agent = DiagnosticsAgent()
correlation_agent = EventCorrelationEngineAgent()
policy_agent = PolicyEnforcementAgent()
remediation_agent = RemediationAgent()
rollback_supervisor = RollbackSupervisor()
