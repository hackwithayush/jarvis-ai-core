"""
Jarvis v14.0 — Laptop System & Security Guardian Engine
Comprehensive real-time diagnostic audit, startup registry registry inspection, event log analysis, and malware scan.
"""
import os
import sys
import subprocess
import platform
import logging
import psutil
import shutil
import re
import json
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("jarvis.security_guardian")

class SystemGuardian:
    """Windows Security and OS Optimization Engine."""

    def __init__(self):
        self.is_windows = platform.system().lower() == "windows"
        from core.root_cause_analyzer import RootCauseAnalyzer
        from core.sandbox_executor import RegistrySandbox, RestrictedProcessExecutor
        self.rca = RootCauseAnalyzer(window_seconds=300)
        self.reg_sandbox = RegistrySandbox()
        self.process_executor = RestrictedProcessExecutor(is_dry_run=False)
        
        # Start proactive remediation loop in a daemon thread
        import threading
        t = threading.Thread(target=self._run_proactive_remediation_loop, args=(300,), daemon=True)
        t.start()

    def _run_proactive_remediation_loop(self, interval_seconds: int = 300):
        """Runs the background monitoring thread and performs self-healing under 80.0 neural health."""
        logger.info("[GUARDIAN DAEMON] Started proactive system remediation daemon.")
        while True:
            try:
                # 1. Gather baseline scans
                sec_scan = self.audit_security_status()
                bug_scan = self.audit_system_bugs()
                health = self.compute_health_score(sec_scan, bug_scan) * 10.0 # scaled to 100.0
                
                logger.info(f"[GUARDIAN DAEMON] Proactive scan complete. Neural Health Score: {health}/100.0")
                
                # 2. Check if health drops below 80.0
                if health < 80.0:
                    logger.warning(f"[GUARDIAN DAEMON] Neural health ({health}/100.0) is below threshold (80.0). Triggering autonomous optimization!")
                    
                    # Import locally to avoid circular import issues!
                    from core.skills_registry import skills_registry
                    
                    # execute "optimize_system" under HIGH clearance
                    context = {
                        "clearance_level": "HIGH",
                        "args": {
                            "deep_clean": True  # auto-remediation uses deep clean to fix paths too
                        }
                    }
                    res = skills_registry.execute_skill("optimize_system", context)
                    logger.info(f"[GUARDIAN DAEMON] Autonomous optimization result: {res}")
            except Exception as e:
                logger.error(f"[GUARDIAN DAEMON] Error in proactive remediation loop: {e}", exc_info=True)
            
            # Sleep for the interval
            time.sleep(interval_seconds)

    def _read_user_path(self) -> str:
        """Reads the user environment PATH variable using Sandbox or actual winreg."""
        if self.reg_sandbox.is_active:
            try:
                val, _ = self.reg_sandbox.query_value("HKCU", "Environment", "Path")
                return val
            except FileNotFoundError:
                return ""
        else:
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
                    val, _ = winreg.QueryValueEx(key, "Path")
                    return val
            except FileNotFoundError:
                return ""

    def _write_user_path(self, value: str):
        """Writes the user environment PATH variable using Sandbox or actual winreg."""
        if self.reg_sandbox.is_active:
            self.reg_sandbox.set_value("HKCU", "Environment", "Path", 1, value)
        else:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, value)

    def audit_security_status(self) -> dict:
        """Audits Windows Defender, Firewall, and startup security."""
        report = {
            "defender_active": False,
            "firewall_active": False,
            "protection_details": {},
            "suspicious_startup_keys": [],
            "suspicious_processes": [],
            "warnings": [],
            "status": "SECURE"
        }

        if not self.is_windows:
            report["warnings"].append("Core diagnostics limited: Host OS is not Windows.")
            report["status"] = "UNSUPPORTED"
            return report

        # 1. Audit Windows Defender via PowerShell
        try:
            cmd = "powershell -Command \"Get-MpComputerStatus | Select-Object -Property AntivirusEnabled, AMServiceEnabled, RealTimeProtectionEnabled, BehaviorMonitorEnabled | ConvertTo-Json\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if data is None or not isinstance(data, dict):
                    report["warnings"].append("Could not fetch Windows Defender status (invalid data format).")
                elif any(data.get(k) is None for k in ["AntivirusEnabled", "AMServiceEnabled", "RealTimeProtectionEnabled", "BehaviorMonitorEnabled"]):
                    report["warnings"].append("Could not fetch Windows Defender status (null properties returned).")
                else:
                    report["defender_active"] = bool(data.get("AntivirusEnabled")) or bool(data.get("AMServiceEnabled"))
                    report["protection_details"] = {
                        "RealTimeProtection": bool(data.get("RealTimeProtectionEnabled")),
                        "BehaviorMonitor": bool(data.get("BehaviorMonitorEnabled"))
                    }
                    if not report["protection_details"]["RealTimeProtection"]:
                        report["warnings"].append("Real-Time protection is disabled on Windows Defender.")
            else:
                report["warnings"].append("Could not fetch Windows Defender status.")
        except Exception as e:
            report["warnings"].append(f"Defender query failure: {e}")

        # 2. Audit Windows Firewall Status
        try:
            cmd = "powershell -Command \"Get-NetFirewallProfile -PolicyStore ActiveStore | Select-Object -Property Name, Enabled | ConvertTo-Json\""
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if data is None:
                    report["warnings"].append("Could not fetch Windows Firewall profile status (invalid data format).")
                else:
                    enabled_values = []
                    if isinstance(data, list):
                        enabled_values = [p.get("Enabled") for p in data if "Enabled" in p]
                    elif isinstance(data, dict):
                        enabled_values = [data.get("Enabled")]
                    
                    if not enabled_values or any(v is None for v in enabled_values):
                        report["warnings"].append("Could not fetch Windows Firewall profile status (null properties returned).")
                    else:
                        report["firewall_active"] = any(bool(v) for v in enabled_values)
                        if not report["firewall_active"]:
                            report["warnings"].append("Active Windows Firewall profile is disabled.")
            else:
                report["warnings"].append("Could not fetch Windows Firewall profile status.")
        except Exception as e:
            report["warnings"].append(f"Firewall query failure: {e}")

        # 3. Audit Startup Registry Keys for Persistence Items
        try:
            import winreg
            startup_paths = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
            ]
            for hkey, path in startup_paths:
                try:
                    with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                        i = 0
                        while True:
                            name, value, _ = winreg.EnumValue(key, i)
                            # Tag suspicious executables in Temp or AppData
                            if any(x in str(value).lower() for x in ["temp", "appdata\\local\\temp", "wscript.exe", "cmd.exe /c"]):
                                report["suspicious_startup_keys"].append({"name": name, "path": value})
                                report["warnings"].append(f"Suspicious persistence key: '{name}' pointing to '{value}'")
                            i += 1
                except OSError:
                    pass # Reached end of registry keys
        except Exception as e:
            report["warnings"].append(f"Registry persistence audit failure: {e}")

        # 4. Audit Suspicious Running Processes
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    name = proc.info['name'].lower()
                    exe_path = proc.info['exe']
                    cmdline = proc.info['cmdline']

                    # Threat pattern A: Masquerading names
                    if name in ["svch0st.exe", "lsass_safe.exe", "explore.exe", "taskmgr_clean.exe"]:
                        report["suspicious_processes"].append({"pid": proc.pid, "name": name, "reason": "Masquerading system process"})
                        report["warnings"].append(f"Masquerader process active: {name} (PID: {proc.pid})")
                    
                    # Threat pattern B: Running from temp folders
                    elif exe_path and any(x in exe_path.lower() for x in ["temp", "appdata\\local\\temp"]):
                        if not any(safe in exe_path.lower() for safe in ["discord", "teams", "slack", "vscode", "chrome"]):
                            report["suspicious_processes"].append({"pid": proc.pid, "name": name, "reason": "Running from temp directory"})
                            report["warnings"].append(f"Process running from TEMP folder: {name} (PID: {proc.pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                    pass
        except Exception as e:
            report["warnings"].append(f"Active process audit failure: {e}")

        if report["warnings"]:
            report["status"] = "THREATS_FOUND" if (report["suspicious_startup_keys"] or report["suspicious_processes"]) else "DEGRADED"

        return report

    def audit_system_bugs(self) -> dict:
        """Audits Windows Event Logs, hardware hogs, environment pathways, and temp bloat."""
        report = {
            "resource_hogs": [],
            "event_log_errors": [],
            "bloat_size_mb": 0,
            "broken_env_paths": [],
            "warnings": [],
            "status": "HEALTHY"
        }

        # 1. Audit CPU and RAM Hogs
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    name = proc.info['name']
                    if not name:
                        continue
                    
                    name_lower = name.lower()
                    if name_lower in ["system idle process", "idle", "system", "registry", "interrupts", "memcompression", "onedrive.exe", "explorer.exe", "msmpeng.exe", "svchost.exe", "searchindexer.exe", "taskmgr.exe"]:
                        continue
                        
                    cpu = proc.info['cpu_percent']
                    mem = proc.info['memory_percent']
                    
                    # Tag heavy hogs
                    if (cpu and cpu > 60) or (mem and mem > 15):
                        report["resource_hogs"].append({
                            "pid": proc.pid,
                            "name": name,
                            "cpu": f"{cpu}%" if cpu else "0%",
                            "mem": f"{mem:.1f}%"
                        })
                        report["warnings"].append(f"Resource hog detected: {name} (CPU: {cpu}%, RAM: {mem:.1f}%)")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            report["warnings"].append(f"Resource hog audit failure: {e}")

        # 2. Audit Windows Event Logs for System Crashes / Errors
        if self.is_windows:
            try:
                cmd = "powershell -Command \"Get-EventLog -LogName System -EntryType Error -Newest 10 | Select-Object -Property Source, Message, TimeGenerated | ConvertTo-Json\""
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                if res.returncode == 0 and res.stdout.strip():
                    import json
                    events = json.loads(res.stdout.strip())
                    if isinstance(events, dict):
                        events = [events]
                    
                    self.rca.clear_buffer()
                    for event in events:
                        report["event_log_errors"].append({
                            "source": event.get("Source", "Unknown"),
                            "message": event.get("Message", "No message details").split("\n")[0],
                            "time": event.get("TimeGenerated", "")
                        })
                        self.rca.feed_event(
                            source=event.get("Source", "Unknown"),
                            message=event.get("Message", "No message details"),
                            time_generated=event.get("TimeGenerated"),
                            severity="ERROR"
                        )
                    if report["event_log_errors"]:
                        report["warnings"].append(f"Detected {len(report['event_log_errors'])} recent OS/driver error logs.")
            except Exception as e:
                report["warnings"].append(f"Event Log query failure: {e}")

        # 3. Audit Temp Bloat
        try:
            temp_paths = []
            if self.is_windows:
                temp_paths.extend([os.environ.get("TEMP", ""), r"C:\Windows\Temp"])
            else:
                temp_paths.append("/tmp")

            total_bytes = 0
            for temp_dir in temp_paths:
                if temp_dir and os.path.exists(temp_dir):
                    for root, _, files in os.walk(temp_dir):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                total_bytes += os.path.getsize(fp)
                            except OSError:
                                pass
            report["bloat_size_mb"] = round(total_bytes / (1024 * 1024), 2)
            if report["bloat_size_mb"] > 1024:
                report["warnings"].append(f"Large bloat detected: Temp folder exceeds {report['bloat_size_mb']} MB.")
        except Exception as e:
            report["warnings"].append(f"Storage bloat audit failure: {e}")

        # 4. Audit Environment Variable Paths
        try:
            path_var = os.environ.get("PATH", "")
            separator = ";" if self.is_windows else ":"
            for path_entry in path_var.split(separator):
                if path_entry and not os.path.exists(path_entry):
                    report["broken_env_paths"].append(path_entry)
            
            if report["broken_env_paths"]:
                report["warnings"].append(f"Orphaned paths in system PATH variable: {len(report['broken_env_paths'])} missing directories.")
        except Exception as e:
            report["warnings"].append(f"Environment variable path audit failure: {e}")

        # Compute dynamic root cause correlation analysis
        cpu_hog_check = {"cpu_percent": 0.0}
        for hog in report["resource_hogs"]:
            try:
                cpu_val = float(str(hog.get("cpu", "0")).replace("%", ""))
                if cpu_val > cpu_hog_check["cpu_percent"]:
                    cpu_hog_check["cpu_percent"] = cpu_val
            except Exception:
                pass
                
        rca_report = self.rca.analyze_correlation(system_load=cpu_hog_check)
        report["root_cause_analysis"] = rca_report
        
        # Append correlation warnings
        if rca_report.get("root_cause_score", 0.0) >= 0.50:
            for vector in rca_report.get("primary_vectors", []):
                report["warnings"].append(f"ROOT CAUSE DETECTED: {vector} (Score: {rca_report.get('root_cause_score')})")

        if report["warnings"]:
            report["status"] = "BUGS_FOUND" if (report["event_log_errors"] or report["resource_hogs"]) else "DEGRADED"

        return report

    def compute_health_score(self, sec_scan: dict, bug_scan: dict) -> float:
        """Computes system health rating from 1.0 to 10.0 based on scan telemetry, ignoring failed queries."""
        score = 10.0
        
        # Check if queries failed/timed out to avoid false penalties
        defender_query_failed = any("Could not fetch Windows Defender" in w or "Defender query failure" in w for w in sec_scan.get("warnings", []))
        firewall_query_failed = any("Could not fetch Windows Firewall" in w or "Firewall query failure" in w for w in sec_scan.get("warnings", []))
        
        # 1. Windows Defender Status
        if not defender_query_failed:
            if not sec_scan.get("defender_active", False):
                score -= 2.5
            details = sec_scan.get("protection_details", {})
            if not details.get("RealTimeProtection", False):
                score -= 1.5
            if not details.get("BehaviorMonitor", False):
                score -= 1.0
            
        # 2. Firewall Status
        if not firewall_query_failed:
            if not sec_scan.get("firewall_active", False):
                score -= 2.5
            
        # 3. Suspicious items & persistence
        score -= len(sec_scan.get("suspicious_startup_keys", [])) * 2.0
        score -= len(sec_scan.get("suspicious_processes", [])) * 2.0
        
        # 4. Storage Bloat (Temp Files)
        bloat_size = bug_scan.get("bloat_size_mb", 0)
        if bloat_size > 1000:
            score -= 1.0
        elif bloat_size > 500:
            score -= 0.2
            
        # 5. Missing system paths (only deduct for actual missing paths detected in the audit)
        score -= len(bug_scan.get("broken_env_paths", [])) * 0.2
        
        # 6. Windows System Event Log Errors
        score -= len(bug_scan.get("event_log_errors", [])) * 0.1
        
        # 7. CPU/RAM Hogs
        score -= len(bug_scan.get("resource_hogs", [])) * 1.5
        
        return max(1.0, min(10.0, round(score, 1)))

    def resolve_threats_and_bugs(self, scan_results: dict, risk_policy: str = "HIGH", approved_actions: list = None) -> dict:
        """Solves identified bugs, purges temp files, flushes DNS, and triggers security fixes with telemetry logging, risk enforcement, and dev-path integrity protection."""
        start_time = time.time()
        actions_taken = []
        errors = []
        risk_classifications = {}
        rollback_snapshot = {}
        
        if not self.is_windows:
            return {"success": False, "actions": [], "errors": ["Forced resolve unsupported on non-Windows systems."]}

        # Define remediation risk classification rules
        RISK_SEVERITY = {
            "clean_temp": {"severity": "LOW", "description": "Purging temporary files. High safety."},
            "flush_dns": {"severity": "LOW", "description": "Flushing DNS resolver cache. High safety."},
            "prune_path": {"severity": "MEDIUM", "description": "Pruning orphaned directories from PATH registry. Captures rollback snapshot."},
            "kill_process": {"severity": "HIGH", "description": "Terminating active CPU/RAM resource hogs. Requires confirmation."},
            "defender_scan": {"severity": "LOW", "description": "Triggering a background Windows Defender malware scan. High safety."}
        }

        # Risk Classification Policy Matrix
        # LOW: auto-fix LOW items, skip MEDIUM and HIGH.
        # MEDIUM: auto-fix LOW items, requires approval for MEDIUM.
        # HIGH: auto-fix LOW/MEDIUM, requires confirmation for HIGH.
        # CRITICAL: simulation only.
        RISK_POLICY_LEVELS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        policy_level = RISK_POLICY_LEVELS.get(risk_policy.upper(), 3)
        is_simulation = (policy_level == 4)
        approved_set = set(item.lower() for item in (approved_actions or []))

        # Activate Sandbox Execution Layer depending on policy scope
        if is_simulation:
            self.reg_sandbox.activate()
            self.process_executor.set_dry_run(True)
        else:
            self.reg_sandbox.deactivate()
            self.process_executor.set_dry_run(False)

        # Baseline dev-tool PATH integrity check before doing any modifications
        dev_tools = ["python", "git", "node", "code"]
        dev_tools_before = {tool: shutil.which(tool) for tool in dev_tools}

        # Calculate initial baseline health score
        sec_before = scan_results.get("security", {})
        bugs_before = scan_results.get("bugs", {})
        health_before = self.compute_health_score(sec_before, bugs_before)

        # 1. Clean Temporary Bloat
        risk_classifications["temp_cleanup"] = RISK_SEVERITY["clean_temp"]
        locked_file_count = 0
        cleaned_mb = 0
        
        if is_simulation:
            # Estimate temp file size
            temp_paths = [os.environ.get("TEMP", ""), r"C:\Windows\Temp"]
            total_bytes = 0
            for temp_dir in temp_paths:
                if temp_dir and os.path.exists(temp_dir):
                    for root, _, files in os.walk(temp_dir):
                        for f in files:
                            try: total_bytes += os.path.getsize(os.path.join(root, f))
                            except: pass
            sim_mb = round(total_bytes / (1024 * 1024), 2)
            actions_taken.append(f"[SIMULATION] Would purge storage bloat: Cleaned {sim_mb} MB from temporary folders.")
        else:
            try:
                temp_dirs = [os.environ.get("TEMP", ""), r"C:\Windows\Temp"]
                for temp_dir in temp_dirs:
                    if temp_dir and os.path.exists(temp_dir):
                        for filename in os.listdir(temp_dir):
                            file_path = os.path.join(temp_dir, filename)
                            try:
                                if os.path.isfile(file_path) or os.path.islink(file_path):
                                    size = os.path.getsize(file_path)
                                    os.unlink(file_path)
                                    cleaned_mb += size
                                elif os.path.isdir(file_path):
                                    size = 0
                                    for root, _, files in os.walk(file_path):
                                        for f in files:
                                            try: size += os.path.getsize(os.path.join(root, f))
                                            except: pass
                                    shutil.rmtree(file_path)
                                    cleaned_mb += size
                            except Exception:
                                locked_file_count += 1
                cleaned_mb = round(cleaned_mb / (1024 * 1024), 2)
                actions_taken.append(f"Purged storage bloat: Cleaned {cleaned_mb} MB from system temporary folders (skipped {locked_file_count} locked files).")
            except Exception as e:
                errors.append(f"Temp folder purge warning: {e}")

        # 2. Flush DNS Cache to resolve networking bugs
        risk_classifications["dns_flush"] = RISK_SEVERITY["flush_dns"]
        if is_simulation:
            actions_taken.append("[SIMULATION] Would flush system DNS Resolver Cache.")
        else:
            try:
                res = subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, text=True)
                if res.returncode == 0:
                    actions_taken.append("Flushed system DNS Resolver Cache (restored network routing stability).")
                else:
                    errors.append("DNS flush command returned non-zero code.")
            except Exception as e:
                errors.append(f"DNS resolver purge failure: {e}")

        # 3. Kill identified Resource Hogs (HIGH risk)
        risk_classifications["hog_termination"] = RISK_SEVERITY["kill_process"]
        hogs = scan_results.get("bugs", {}).get("resource_hogs", [])
        if hogs:
            # Check high-risk authorization policy: requires confirmation (must be in approved_actions)
            hog_allowed = False
            hog_reason = ""
            if is_simulation:
                hog_reason = "CRITICAL policy (simulation only)"
            elif "hog_termination" in approved_set:
                hog_allowed = True
            else:
                hog_reason = "Requires explicit operator confirmation under HIGH risk policy"
                
            if not hog_allowed:
                actions_taken.append(f"[SKIPPED] Resource hog neutralization: {hog_reason} for processes: {', '.join([h.get('name') for h in hogs])}.")
            else:
                for hog in hogs:
                    pid = hog.get("pid")
                    name = hog.get("name")
                    actions_taken.append(f"[SKIPPED] VULNERABILITY PATCHED: Auto-kill disabled for '{name}' (PID: {pid}) to prevent accidental termination of user applications.")
        
        # 4. Trigger Windows Defender scan if threats found
        sec_warnings = scan_results.get("security", {}).get("warnings", [])
        has_sec_threats = scan_results.get("security", {}).get("suspicious_startup_keys") or scan_results.get("security", {}).get("suspicious_processes")
        
        if has_sec_threats or any("disabled" in w.lower() for w in sec_warnings):
            risk_classifications["defender_trigger"] = RISK_SEVERITY["defender_scan"]
            if is_simulation:
                actions_taken.append("[SIMULATION] Would trigger background Windows Defender Quick Malware Scan.")
            else:
                try:
                    subprocess.Popen("powershell -Command \"Start-MpScan -ScanType QuickScan\"", shell=True)
                    actions_taken.append("Triggered background Windows Defender Quick Malware Scan (Start-MpScan).")
                except Exception as e:
                    errors.append(f"Could not automate Windows Defender quick scan: {e}")

        # 5. Prune Orphaned PATH entries from HKCU Environment Registry with Rollback & Non-blocking Broadcast
        broken_paths = scan_results.get("bugs", {}).get("broken_env_paths", [])
        new_entries = []
        pruned_paths_count = 0
        if broken_paths and self.is_windows:
            risk_classifications["path_repair"] = RISK_SEVERITY["prune_path"]
            
            # Check medium-risk authorization policy:
            # policy_level >= 3 (HIGH) allows auto-fix, policy_level == 2 (MEDIUM) requires approval
            path_allowed = False
            path_reason = ""
            if is_simulation:
                path_allowed = True
            elif policy_level >= 3:
                path_allowed = True
            elif policy_level == 2:
                if "path_repair" in approved_set:
                    path_allowed = True
                else:
                    path_reason = "Requires operator approval under MEDIUM risk policy"
            else:
                path_reason = "Requires higher risk allowance under LOW risk policy"
                
            if not path_allowed:
                actions_taken.append(f"[SKIPPED] Registry PATH pruning: {path_reason}.")
            else:
                try:
                    pruned_paths = []
                    value = self._read_user_path()
                    rollback_snapshot["Path"] = value  # Rollback checkpoint
                    
                    path_entries = value.split(";")
                    for entry in path_entries:
                        entry_strip = entry.strip()
                        if not entry_strip:
                            continue
                        
                        expanded = os.path.expandvars(entry_strip)
                        is_broken = False
                        for bp in broken_paths:
                            if bp.lower() == entry_strip.lower() or bp.lower() == expanded.lower():
                                is_broken = True
                                break
                        
                        if is_broken:
                            pruned_paths.append(entry_strip)
                        else:
                            new_entries.append(entry_strip)
                    
                    if pruned_paths:
                        pruned_paths_count = len(pruned_paths)
                        new_path_str = ";".join(new_entries)
                        self._write_user_path(new_path_str)
                        
                        # Asynchronous/Non-blocking setting change broadcast (Prevents system hangs!)
                        if not self.reg_sandbox.is_active:
                            try:
                                import ctypes
                                HWND_BROADCAST = 0xffff
                                WM_SETTINGCHANGE = 0x001a
                                ctypes.windll.user32.SendNotifyMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
                            except Exception as ex:
                                logger.warning(f"Failed to broadcast WM_SETTINGCHANGE: {ex}")
                        
                        prefix = "[SIMULATION] Would prune" if self.reg_sandbox.is_active else "Pruned"
                        actions_taken.append(f"{prefix} {len(pruned_paths)} orphaned/missing directories from User PATH: {', '.join(pruned_paths)}")
                except Exception as e:
                    errors.append(f"Failed to prune orphaned PATH entries from Registry: {e}")

        # 6. Check HKLM System Path for broken entries (ReadOnly/Telemetry only due to elevation)
        if self.is_windows:
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_READ) as key:
                    try:
                        sys_path_val, _ = winreg.QueryValueEx(key, "Path")
                        sys_path_entries = sys_path_val.split(";")
                        broken_sys_paths = []
                        for entry in sys_path_entries:
                            entry_strip = entry.strip()
                            if not entry_strip:
                                continue
                            expanded = os.path.expandvars(entry_strip)
                            # Check if matches any broken path
                            for bp in broken_paths:
                                if bp.lower() == entry_strip.lower() or bp.lower() == expanded.lower():
                                    broken_sys_paths.append(entry_strip)
                        
                        if broken_sys_paths:
                            actions_taken.append(f"Identified {len(broken_sys_paths)} missing paths in HKLM (System PATH): {', '.join(broken_sys_paths)}. Skipping pruning: Requires administrator elevation.")
                            risk_classifications["system_path_repair"] = {
                                "severity": "HIGH",
                                "description": "Pruning HKLM System PATH. Skipped due to required admin privileges."
                            }
                    except FileNotFoundError:
                        pass
            except Exception as e:
                logger.warning(f"Failed to audit HKLM path: {e}")

        # 7. Dev-tool PATH Integrity Post-Check and Auto-Rollback Circuit
        regressions = []
        if not is_simulation:
            dev_tools_after = {tool: shutil.which(tool) for tool in dev_tools}
            regressions = [t for t in dev_tools if dev_tools_before[t] and not dev_tools_after[t]]
            
            if regressions:
                actions_taken.append(f"CRITICAL REGRESSION DETECTED: Pruning broke developer tools ({', '.join(regressions)}). Triggering auto-rollback.")
                # Restore registry path from checkpoint
                if rollback_snapshot.get("Path") and self.is_windows:
                    try:
                        import winreg
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                            winreg.SetValueEx(key, "Path", 0, winreg.REG_SZ, rollback_snapshot["Path"])
                        # Re-broadcast env change
                        try:
                            import ctypes
                            HWND_BROADCAST = 0xffff
                            WM_SETTINGCHANGE = 0x001a
                            ctypes.windll.user32.SendNotifyMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
                        except:
                            pass
                        actions_taken.append("Rollback executed successfully: User PATH registry restored to healthy baseline.")
                    except Exception as restore_err:
                        errors.append(f"Auto-rollback failure: {restore_err}")

        # Compute post-repair health score (actual post-state scan)
        sec_after = self.audit_security_status()
        bugs_after = self.audit_system_bugs()
        health_after = self.compute_health_score(sec_after, bugs_after)

        duration = round(time.time() - start_time, 3)

        # Generate structured JSON repair telemetry report
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        report_filename = f"repair_report_{timestamp_str}.json"
        report_path = os.path.join(log_dir, report_filename)
        latest_report_path = os.path.join(log_dir, "latest_repair_report.json")

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "risk_policy": risk_policy.upper(),
            "approved_actions": list(approved_set),
            "pre_repair_score": health_before,
            "post_repair_score": health_after,
            "pre_repair_warnings": sec_before.get("warnings", []) + bugs_before.get("warnings", []),
            "post_repair_warnings": sec_after.get("warnings", []) + bugs_after.get("warnings", []),
            "actions_taken": actions_taken,
            "errors_encountered": errors,
            "rollback_snapshot": rollback_snapshot,
            "risk_classifications": risk_classifications,
            "metrics": {
                "temp_mb_cleaned": cleaned_mb,
                "locked_files_skipped": locked_file_count,
                "paths_pruned_count": pruned_paths_count,
                "path_integrity_regressions": regressions,
                "system_path_pruning_skipped": "Requires admin elevation" if self.is_windows else "N/A"
            }
        }

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=4)
            with open(latest_report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=4)
            actions_taken.append(f"Generated structured repair telemetry JSON: 'logs/{report_filename}' (and updated 'logs/latest_repair_report.json').")
        except Exception as e:
            errors.append(f"Failed to write structured log report: {e}")

        return {
            "success": len(actions_taken) > 0,
            "actions": actions_taken,
            "errors": errors,
            "telemetry": report_data
        }

# Global Instance
system_guardian = SystemGuardian()
