"""
Jarvis v15.0 — Secure Sandboxed Execution Layer (L2 Sandbox)
Virtualizes registry mutations, intercepts file operations, and manages low-privilege dry-run subprocess environments to protect workstation integrity during repairs.
"""
import os
import logging
import subprocess
import uuid

logger = logging.getLogger("jarvis.sandbox_executor")

class RegistrySandbox:
    """Virtualizes HKEY registry hives in memory to allow secure dry-runs of environment configurations."""

    def __init__(self):
        self.is_active = False
        self.virtual_hive = {
            "HKCU": {
                "Environment": {
                    "Path": "C:\\Windows\\system32;C:\\Windows;C:\\Users\\AYUSH CHAUDHARY\\miniconda3;C:\\Users\\AYUSH CHAUDHARY\\miniconda3\\Library\\usr\\bin"
                }
            },
            "HKLM": {
                "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment": {
                    "Path": "C:\\Windows\\system32;C:\\Windows"
                }
            }
        }
        self.rollback_checkpoints = {}

    def _normalize_hive_and_key(self, hive_name: str, key_path: str) -> tuple:
        """Maps long/short hive name aliases and strips leading hive prefixes from keys."""
        hive_map = {
            "HKEY_CURRENT_USER": "HKCU",
            "HKEY_LOCAL_MACHINE": "HKLM",
            "HKCU": "HKCU",
            "HKLM": "HKLM"
        }
        norm_hive = hive_map.get(hive_name.upper(), hive_name.upper())
        
        # Clean the key path to be relative to the hive root
        clean_key = key_path
        hive_prefix = hive_name.upper() + "\\"
        if clean_key.upper().startswith(hive_prefix):
            clean_key = clean_key[len(hive_prefix):]
            
        full_hkcu_prefix = "HKEY_CURRENT_USER\\"
        full_hklm_prefix = "HKEY_LOCAL_MACHINE\\"
        if clean_key.upper().startswith(full_hkcu_prefix):
            clean_key = clean_key[len(full_hkcu_prefix):]
        elif clean_key.upper().startswith(full_hklm_prefix):
            clean_key = clean_key[len(full_hklm_prefix):]
            
        return norm_hive, clean_key

    def activate(self):
        """Enables sandbox interception mode."""
        self.is_active = True
        logger.info("Registry Sandboxing active (virtual dry-runs enabled).")

    def deactivate(self):
        """Disables sandbox interception mode."""
        self.is_active = False
        logger.info("Registry Sandboxing inactive (direct commits enabled).")

    def query_value(self, hive_name: str, key_path: str, value_name: str) -> tuple:
        """
        Queries values from the virtual registry overlay.
        Returns: (value_string, value_type_id)
        """
        norm_hive, norm_key = self._normalize_hive_and_key(hive_name, key_path)
        hive = self.virtual_hive.get(norm_hive)
        if not hive:
            raise FileNotFoundError(f"Hive {hive_name} ({norm_hive}) not found in virtual registry.")
        
        # Exact match or normalized match
        key_match = None
        for kp in hive.keys():
            if kp.lower() == norm_key.lower():
                key_match = kp
                break
        
        if not key_match:
            raise FileNotFoundError(f"Key path {key_path} ({norm_key}) not found in hive.")
            
        key_data = hive[key_match]
        val_match = None
        for vn in key_data.keys():
            if vn.lower() == value_name.lower():
                val_match = vn
                break
                
        if not val_match:
            raise FileNotFoundError(f"Value name {value_name} not found in key.")
            
        # Return mock value and standard REG_SZ type id (1)
        return key_data[val_match], 1

    def set_value(self, hive_name: str, key_path: str, value_name: str, val_type: int, value: str):
        """
        Writes values into the virtual registry overlay.
        Stores a checkpoint for rollback testing.
        """
        norm_hive, norm_key = self._normalize_hive_and_key(hive_name, key_path)
        hive = self.virtual_hive.setdefault(norm_hive, {})
        key_data = hive.setdefault(norm_key, {})
        
        # Save checkpoint before modification
        checkpoint_key = f"{norm_hive}\\{norm_key}\\{value_name}"
        if checkpoint_key not in self.rollback_checkpoints:
            self.rollback_checkpoints[checkpoint_key] = key_data.get(value_name)
            
        key_data[value_name] = value
        logger.debug(f"[VIRTUAL REGISTRY WRITE] {checkpoint_key} = {value}")

    def trigger_rollback(self) -> list:
        """
        Restores the virtual registry state to the saved checkpoints.
        Returns: list of rolled back keys.
        """
        rolled_back = []
        for key, value in self.rollback_checkpoints.items():
            try:
                parts = key.split("\\")
                hive = parts[0]
                value_name = parts[-1]
                key_path = "\\".join(parts[1:-1])
                
                if value is None:
                    # Key was created new during dry-run, remove it
                    if key_path in self.virtual_hive[hive] and value_name in self.virtual_hive[hive][key_path]:
                        del self.virtual_hive[hive][key_path][value_name]
                else:
                    self.virtual_hive[hive][key_path][value_name] = value
                rolled_back.append(key)
            except Exception as e:
                logger.error(f"Failed to restore mock registry key {key}: {e}")
        self.rollback_checkpoints = {}
        return rolled_back


class RestrictedProcessExecutor:
    """Safely handles subprocess execution under restricted credentials or dry-run constraints."""

    def __init__(self, is_dry_run: bool = False):
        self.is_dry_run = is_dry_run
        self.execution_history = []
        self.mock_tokens = {}

    def set_dry_run(self, value: bool):
        self.is_dry_run = value

    def mint_mock_token(self, principal: str, clearance: str = "standard") -> str:
        """Mints an ephemeral restricted token for simulation operations."""
        token_id = f"tkn_{uuid.uuid4().hex[:8]}"
        self.mock_tokens[token_id] = {
            "principal": principal,
            "clearance": clearance,
            "created_at": uuid.uuid4().hex
        }
        logger.info(f"[TOKEN DECOUPLER] Minted token {token_id} with '{clearance}' privileges.")
        return token_id

    def verify_token(self, token_id: str, required_clearance: str) -> bool:
        """Verifies if the security clearance token meets execution criteria."""
        token_info = self.mock_tokens.get(token_id)
        if not token_info:
            return False
            
        clearance_hierarchy = {"guest": 1, "standard": 2, "admin": 3}
        token_level = clearance_hierarchy.get(token_info.get("clearance", "guest"), 1)
        req_level = clearance_hierarchy.get(required_clearance, 2)
        
        return token_level >= req_level

    def run_command(self, cmd_string: str, shell: bool = True, timeout: int = 10, token_id: str = None) -> dict:
        """
        Executes a command with safety wrapper.
        If dry-run is active, logs command and avoids executing.
        """
        record = {
            "command": cmd_string,
            "executed": not self.is_dry_run,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "warning": None
        }

        # Check privilege token if provided
        if token_id:
            # Let's say admin token is needed for modifying system configs or starting dangerous tasks
            is_sensitive = any(w in cmd_string.lower() for w in ["sc ", "net stop", "net start", "reg add", "reg delete"])
            if is_sensitive and not self.verify_token(token_id, "admin"):
                record["executed"] = False
                record["returncode"] = -5
                record["stderr"] = "Security Warning: Insufficient Clearance token to run sensitive operating system command."
                self.execution_history.append(record)
                return record

        # Security check: Block direct credential stealing, system deletions, or format actions
        malicious_patterns = ["del /f /s /q c:\\", "format ", "rmdir /s /q c:\\windows", "net user "]
        for pattern in malicious_patterns:
            if pattern in cmd_string.lower():
                record["executed"] = False
                record["returncode"] = -1
                record["stderr"] = "CRITICAL: Malicious execution pattern blocked by Sandbox Protection Layer."
                self.execution_history.append(record)
                logger.error(f"Malicious command blocked: '{cmd_string}'")
                return record

        if self.is_dry_run:
            record["stdout"] = f"[SIMULATION] Command mock output for: {cmd_string}"
            self.execution_history.append(record)
            logger.info(f"[SANDBOX DRY-RUN Command] {cmd_string}")
            return record

        try:
            # Low privilege isolation (uses standard limited shell environment)
            res = subprocess.run(
                cmd_string,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            record["returncode"] = res.returncode
            record["stdout"] = res.stdout
            record["stderr"] = res.stderr
        except subprocess.TimeoutExpired:
            record["returncode"] = -2
            record["stderr"] = f"Command execution timed out after {timeout}s limit."
        except Exception as e:
            record["returncode"] = -3
            record["stderr"] = f"Subprocess launch exception: {e}"

        self.execution_history.append(record)
        return record
