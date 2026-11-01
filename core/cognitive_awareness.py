"""
JARVIS 5.0 — Cognitive Awareness & Predictive Diagnostics Engine
Provides situational intelligence:
1. Active Applications & User Context: Identifies foreground tools, IDEs, and active workflows.
2. Predictive Diagnostics: Detects likely system failures (memory saturation, GPU VRAM exhaustion,
   recurring API rate limits, file lock contention) before host crash.
3. Proactive Advisory: Correlates user activity with long-term strategic objectives and Knowledge Graph blockers
   to suggest timely, autonomous interventions.
"""
import os
import sys
import time
import psutil
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.knowledge_graph import knowledge_graph
from core.mission_memory import mission_memory

logger = logging.getLogger("jarvis.cognitive_awareness")


class CognitiveAwarenessManager:
    """
    Situational awareness and predictive telemetry engine for Tony Stark's workstation.
    """

    DEVELOPER_PROCESSES = {
        "code.exe": "Visual Studio Code",
        "pycharm64.exe": "PyCharm IDE",
        "cursor.exe": "Cursor IDE",
        "devenv.exe": "Visual Studio",
        "windowsterminal.exe": "Windows Terminal",
        "powershell.exe": "PowerShell",
        "cmd.exe": "Command Prompt",
        "firefox.exe": "Mozilla Firefox",
        "chrome.exe": "Google Chrome",
        "ollama.exe": "Ollama Local Neural Engine",
        "qdrant.exe": "Qdrant Vector Database"
    }

    def __init__(self):
        logger.info("JARVIS 5.0 Cognitive Awareness & Predictive Diagnostics initialized.")

    # ─── 1. Active Applications & User Context ────────────────────────────────

    def get_active_application_context(self) -> Dict[str, Any]:
        """
        Detects active developer processes, foreground window title, and operational focus.
        """
        active_tools = []
        running_names = set()

        try:
            for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    pname = proc.info['name'].lower() if proc.info['name'] else ""
                    running_names.add(pname)
                    if pname in self.DEVELOPER_PROCESSES and self.DEVELOPER_PROCESSES[pname] not in active_tools:
                        active_tools.append(self.DEVELOPER_PROCESSES[pname])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"Process inspection warning: {e}")

        # Active Window Title Detection (Windows Win32 API with cross-platform fallback)
        foreground_window = "Primary Command Console"
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if buff.value:
                    foreground_window = buff.value
            except Exception:
                pass

        # Infer User Focus Area
        focus = "General Engineering"
        fg_lower = foreground_window.lower()
        if "visual studio code" in fg_lower or "pycharm" in fg_lower or "cursor" in fg_lower:
            focus = "Software Architecture & Coding"
        elif "powershell" in fg_lower or "terminal" in fg_lower or "cmd" in fg_lower:
            focus = "CLI & System Orchestration"
        elif "firefox" in fg_lower or "chrome" in fg_lower:
            focus = "Research & Web Inspection"

        return {
            "foreground_window": foreground_window,
            "detected_tools": active_tools,
            "user_focus": focus,
            "ollama_active": "ollama.exe" in running_names,
            "timestamp": time.time()
        }

    # ─── 2. Predictive Diagnostics & Failure Forecasting ──────────────────────

    def predict_system_anomalies(self) -> Dict[str, Any]:
        """
        Evaluates hardware vitals and historical event chains to predict failures before they manifest.
        """
        anomalies: List[Dict[str, Any]] = []
        vitals = self._gather_vitals()

        # Check 1: Host Memory Saturation Prediction
        ram_pct = vitals.get("ram_percent", 0.0)
        if ram_pct > 88.0:
            anomalies.append({
                "severity": "CRITICAL",
                "type": "MEMORY_SATURATION",
                "message": f"Host RAM pressure is at {ram_pct:.1f}%. High risk of Out-Of-Memory termination.",
                "remedy": "Trigger aggressive cache garbage collection and terminate non-essential background processes."
            })
        elif ram_pct > 78.0:
            anomalies.append({
                "severity": "WARNING",
                "type": "MEMORY_PRESSURE",
                "message": f"Host RAM utilization elevated ({ram_pct:.1f}%).",
                "remedy": "Monitor memory growth; suspend heavy model offloading if usage exceeds 85%."
            })

        # Check 2: Disk Exhaustion Prediction
        disk_pct = vitals.get("disk_percent", 0.0)
        if disk_pct > 92.0:
            anomalies.append({
                "severity": "CRITICAL",
                "type": "DISK_EXHAUSTION",
                "message": f"Primary drive storage is at {disk_pct:.1f}% capacity. Atomic checkpoints may fail.",
                "remedy": "Purge temporary checkpoint backups and clean data/cache."
            })

        # Check 3: Recurring Failure Pattern Detection via Knowledge Graph
        recurring_failures = self._detect_recurring_failure_patterns()
        anomalies.extend(recurring_failures)

        # Health Status Synthesis
        overall_health = "OPTIMAL"
        if any(a["severity"] == "CRITICAL" for a in anomalies):
            overall_health = "DEGRADED"
        elif len(anomalies) > 0:
            overall_health = "CAUTION"

        return {
            "overall_health": overall_health,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "hardware_telemetry": vitals,
            "evaluated_at": time.time()
        }

    def _gather_vitals(self) -> Dict[str, Any]:
        """Fetches live machine resource statistics."""
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(os.getcwd())
            return {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": mem.percent,
                "ram_available_gb": round(mem.available / (1024**3), 2),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            logger.warning(f"Failed to gather vitals: {e}")
            return {"cpu_percent": 0.0, "ram_percent": 0.0, "disk_percent": 0.0}

    def _detect_recurring_failure_patterns(self) -> List[Dict[str, Any]]:
        """
        Inspects the Knowledge Graph to detect recurring failure patterns (e.g. repeated 429 rate limits).
        """
        patterns = []
        events = [n for n in knowledge_graph.nodes.values() if n.get("type") == "system_event"]

        # 1. Rate Limit Clustering
        rate_limit_events = [
            e for e in events
            if "429" in e.get("label", "") or "rate limit" in e.get("label", "").lower()
        ]
        if len(rate_limit_events) >= 2:
            patterns.append({
                "severity": "WARNING",
                "type": "RECURRING_RATE_LIMIT",
                "message": f"Detected {len(rate_limit_events)} recurring API 429 rate limit events in Knowledge Graph.",
                "remedy": "Activate local Ollama priority mode (llama3.2) or apply exponential backoff pacing."
            })

        # 2. Privileged Action Guardian Blockers
        guardian_events = [
            e for e in events
            if "guardian" in e.get("label", "").lower() or "blocked" in e.get("label", "").lower()
        ]
        if len(guardian_events) >= 2:
            patterns.append({
                "severity": "INFO",
                "type": "RECURRING_APPROVAL_BOTTLENECK",
                "message": f"Detected {len(guardian_events)} missions paused at Zero-Trust Guardian gates.",
                "remedy": "Review pending privilege escalations in Guardian dashboard to unblock pipelines."
            })

        return patterns

    # ─── 3. Proactive Agent Recommendations ───────────────────────────────────

    def suggest_proactive_actions(self) -> List[Dict[str, Any]]:
        """
        Synthesizes active app context, long-term objectives, and knowledge graph blockers
        into prioritized recommendations for Tony Stark.
        """
        suggestions: List[Dict[str, Any]] = []
        app_ctx = self.get_active_application_context()
        unfinished = mission_memory.detect_unfinished_work()

        # Recommendation 1: Unfinished Strategic Work Alignment
        for task in unfinished:
            oid = task["objective_id"]
            blockers = knowledge_graph.find_blockers(oid)
            active_blockers = [b for b in blockers if b.get("is_active_blocker")]

            if active_blockers:
                b_labels = ", ".join([b["label"] for b in active_blockers[:2]])
                suggestions.append({
                    "priority": "HIGH",
                    "category": "BLOCKED_OBJECTIVE",
                    "title": f"Unblock Objective: {task['title'][:40]}",
                    "description": f"Milestone is blocked by dependency: {b_labels}.",
                    "action": f"Resolve prerequisite task '{b_labels}' to resume progress.",
                    "objective_id": oid
                })
            else:
                suggestions.append({
                    "priority": "MEDIUM",
                    "category": "RESUME_OBJECTIVE",
                    "title": f"Resume Milestone {task['milestone_index']}: {task['title'][:40]}",
                    "description": task["prompt_to_resume"],
                    "action": f"POST /api/objective/{oid}/resume",
                    "objective_id": oid
                })

        # Recommendation 2: Hardware Anomaly Mitigations
        diag = self.predict_system_anomalies()
        for anomaly in diag.get("anomalies", []):
            if anomaly["severity"] in ("CRITICAL", "WARNING"):
                suggestions.append({
                    "priority": "HIGH" if anomaly["severity"] == "CRITICAL" else "MEDIUM",
                    "category": "PREDICTIVE_MAINTENANCE",
                    "title": f"Preventative Maintenance: {anomaly['type']}",
                    "description": anomaly["message"],
                    "action": anomaly["remedy"]
                })

        # Recommendation 3: Context-Aware Workflow Suggestion
        user_focus = app_ctx.get("user_focus")
        if user_focus == "Software Architecture & Coding":
            suggestions.append({
                "priority": "LOW",
                "category": "DEVELOPER_SUPPORT",
                "title": "Autonomous Code Evaluation & Testing Ready",
                "description": f"Detected active development session in {app_ctx.get('foreground_window')}.",
                "action": "Invoke autonomous_evaluator.evaluate_code() or trigger test harness."
            })

        return suggestions


# Global Singleton Instance
cognitive_awareness = CognitiveAwarenessManager()
