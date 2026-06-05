"""
Jarvis v14.0 — Event Correlation & Root Cause Intelligence Engine (ECRCI)
Analyzes temporal system logs and telemetry metrics using sliding correlation windows to diagnose systemic faults and predict potential workstation instability.
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("jarvis.root_cause_analyzer")

class RootCauseAnalyzer:
    """Windows temporal event correlation and root cause prediction engine."""

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self.event_buffer = []

    def clear_buffer(self):
        """Clears the event log correlation buffer."""
        self.event_buffer = []

    def feed_event(self, source: str, message: str, time_generated: str = None, severity: str = "ERROR", event_id: int = 0):
        """
        Feeds a diagnostic symptom or system event log into the sliding window buffer.
        """
        # Parse time_generated if present, else use current local time
        parsed_time = None
        if time_generated:
            try:
                # Handle standard powershell JSON serialized dates e.g. "/Date(1779335045000)/"
                if "/Date(" in time_generated:
                    millis = int(time_generated.split("(")[1].split(")")[0])
                    parsed_time = datetime.fromtimestamp(millis / 1000.0)
            except Exception as e:
                logger.debug(f"Failed to parse event date '{time_generated}': {e}")
        
        if parsed_time is None:
            parsed_time = datetime.now()

        self.event_buffer.append({
            "timestamp": parsed_time,
            "source": source,
            "message": message,
            "severity": severity.upper(),
            "event_id": event_id
        })
        self._prune_expired_events()

    def _prune_expired_events(self):
        """Removes events older than the defined correlation sliding window."""
        cutoff = datetime.now() - timedelta(seconds=self.window_seconds)
        # Sort and filter
        self.event_buffer = [e for e in self.event_buffer if e["timestamp"] > cutoff]

    def analyze_correlation(self, system_load: dict = None) -> dict:
        """
        Correlates buffered system logs and performance symptoms to deduce systemic root causes.
        """
        self._prune_expired_events()
        
        analysis = {
            "root_cause_score": 0.0,
            "primary_vectors": [],
            "predicted_failure": None,
            "recommended_remediations": [],
            "remediation_override": False  # If True, bypass auto-fix to prevent active driver crashes
        }

        # Extract system event log properties
        tpm_events = [e for e in self.event_buffer if "TPM" in e["source"].upper() or e["event_id"] == 86]
        bluetooth_events = [e for e in self.event_buffer if "BTHUSB" in e["source"].upper()]
        service_failures = [e for e in self.event_buffer if "SERVICE CONTROL MANAGER" in e["source"].upper()]
        abrupt_shutdowns = [e for e in self.event_buffer if "EVENTLOG" in e["source"].upper() and "unexpected" in e["message"].lower()]
        
        # Extract system performance thresholds
        cpu_load = 0.0
        ram_load = 0.0
        if system_load:
            cpu_load = float(str(system_load.get("cpu_percent", "0")).replace("%", ""))
            ram_load = float(str(system_load.get("ram_percent", "0")).replace("%", ""))

        # 1. Hardware Bus / Controller Co-instability Vector (TPM-WMI + BTHUSB Driver Failures)
        if tpm_events and bluetooth_events:
            analysis["root_cause_score"] = 0.85
            analysis["primary_vectors"].append("Hardware Bus Interface Failure (TPM + Bluetooth Driver Intersect)")
            analysis["predicted_failure"] = "PCIe Controller Hang or USB Hub Disconnect"
            analysis["recommended_remediations"].append("Perform complete system power cycle (Cold Boot) to reset PCIe controller registers.")
            analysis["recommended_remediations"].append("Inspect Windows Device Manager for PCIe Link-State Power Management warnings.")
            analysis["remediation_override"] = True  # Safety: do not perform active registry or file repair on failing hardware controllers

        # 2. Unstable Kernel State Cycle Vector (Unexpected Shutdown preceded by high resource metrics)
        elif abrupt_shutdowns:
            analysis["root_cause_score"] = 0.90
            analysis["primary_vectors"].append("Kernel Power Cycle Fault (Abrupt System Shutdown)")
            if cpu_load > 80.0 or ram_load > 90.0:
                analysis["predicted_failure"] = "Thermal Throttle or Power Draw Crash"
                analysis["recommended_remediations"].append("Audit system cooling hardware and thermal throttle thresholds.")
            else:
                analysis["predicted_failure"] = "Kernel Panic or Transient OS Driver Lockup"
                analysis["recommended_remediations"].append("Run system integrity utilities (sfc /scannow and DISM) to repair potential system file corruption.")
            
        # 3. Startup Crash Loop Vector (Recurrent Service startup failure within sliding window)
        elif len(service_failures) >= 2:
            analysis["root_cause_score"] = 0.70
            analysis["primary_vectors"].append(f"Application Service Startup Loop ({len(service_failures)} failures in window)")
            crashed_services = list(set([e["message"].split("service")[0].strip() for e in service_failures if "service" in e["message"]]))
            analysis["predicted_failure"] = f"Dependency Lockup on services: {', '.join(crashed_services)}"
            analysis["recommended_remediations"].append("Restart System Event Notification Service (SENS) or set crashing service start modes to Automatic (Delayed).")

        # 4. Resource thrashing vector
        elif cpu_load > 90.0:
            analysis["root_cause_score"] = 0.60
            analysis["primary_vectors"].append("Active Resource Exhaustion (CPU > 90%)")
            analysis["predicted_failure"] = "OS Thread Starvation or Core Overhead Thrashing"
            analysis["recommended_remediations"].append("Audit active process execution footprints and limit background scheduler intervals.")

        # Baseline: Healthy / Single unrelated alerts
        if not analysis["primary_vectors"]:
            if self.event_buffer:
                analysis["root_cause_score"] = 0.20
                analysis["primary_vectors"].append("Isolated Diagnostic Alerts (Uncorrelated Warnings)")
                analysis["recommended_remediations"].append("Perform regular preventative workstation maintenance audits.")
            else:
                analysis["root_cause_score"] = 0.0

        return analysis
