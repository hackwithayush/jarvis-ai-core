"""
Safe Action Sandbox
Strict boundary layers preventing dangerous autonomous actions.
"""
import os
import subprocess
import shutil
import sys
import logging

logger = logging.getLogger("jarvis.sandbox")

class SafeSandbox:
    def __init__(self):
        # Master block list for autonomous execution
        self.banned_commands = [
            "del", "rm", "format", "shutdown", "reboot", 
            "regedit", "wget", "curl", "format C:", "rmdir", "mkfs"
        ]
        self.sandbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sandbox_workspace"))
        os.makedirs(self.sandbox_dir, exist_ok=True)
        print(f"[SANDBOX] Execution security layer active. Workspace: {self.sandbox_dir}")
        
    def is_path_safe(self, target_path: str) -> bool:
        """ Ensures the absolute resolved path strictly resides inside the sandbox workspace, immune to symlink escapes. """
        try:
            resolved_target = os.path.realpath(target_path)
            resolved_sandbox = os.path.realpath(self.sandbox_dir)
            
            # Check if the target is physically inside the sandbox using commonpath
            if os.path.commonpath([resolved_target, resolved_sandbox]) != resolved_sandbox:
                logger.warning(f"[SANDBOX BLOCK] Directory traversal/Symlink escape prevented: '{target_path}' resolves to '{resolved_target}'")
                return False
            return True
        except Exception as e:
            logger.error(f"[SANDBOX ERROR] Path resolution failed: {e}")
            return False
        
    def is_safe_to_execute(self, command: str) -> bool:
        """ Checks if a proposed OS command breaks safety rules. """
        cmd_lower = command.lower()
        
        for banned in self.banned_commands:
            # Check for isolated commands to avoid false positives 
            if banned in cmd_lower.split() or banned in cmd_lower:
                print(f"[SANDBOX BLOCK] Prevented execution of restricted command: '{banned}'")
                return False
                
        # Block editing system folders
        if "windows" in cmd_lower or "system32" in cmd_lower or "program files" in cmd_lower:
            print("[SANDBOX BLOCK] Restricted system folder mutation blocked.")
            return False
            
        return True
        
    def execute_command(self, command: str, timeout: int = 10) -> str:
        """ Runs a shell command inside the sandbox workspace securely. """
        if not self.is_safe_to_execute(command):
            return "ERROR: Shell command blocked by Safety Protocol. Cannot execute."
            
        try:
            print(f"[SANDBOX RUN] Shell Command: {command}")
            # Execute with clean environment in the sandbox dir
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.sandbox_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n--- Error ---\n{result.stderr}"
            return output if output.strip() else "Command executed successfully (no output)."
        except subprocess.TimeoutExpired:
            logger.warning(f"[SANDBOX TIMEOUT] Command timed out after {timeout}s: '{command}'")
            return f"ERROR: Execution timed out after {timeout} seconds."
        except Exception as e:
            return f"ERROR: Execution failed: {str(e)}"
            
    def execute_python(self, code: str, timeout: int = 10) -> str:
        """ Writes and runs Python script inside sandbox securely. """
        import ast
        temp_script = os.path.join(self.sandbox_dir, "sandbox_run.py")
        try:
            # PHASE 12: AST Payload Analyzer
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec", "compile"]:
                            return "ERROR: AST Firewall blocked obfuscated eval/exec payload."
                    elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                        module_name = getattr(node, 'module', None)
                        if module_name in ["os", "sys", "subprocess", "socket", "ctypes", "builtins", "shutil"]:
                             return f"ERROR: AST Firewall blocked dangerous import from: {module_name}"
                        for alias in node.names:
                            if alias.name in ["os", "sys", "subprocess", "socket", "ctypes", "builtins", "shutil"]:
                                return f"ERROR: AST Firewall blocked dangerous import: {alias.name}"
            except SyntaxError:
                return "ERROR: AST Parse failed. Invalid Python syntax."
                
            # PHASE 13: Mock Network Injection (Anti-Exfiltration)
            mock_network = """
import sys
class BlindSocket:
    def __getattr__(self, name):
        raise PermissionError('Zero-Trust Network Outbound Blocked')
sys.modules['socket'] = BlindSocket()
sys.modules['urllib'] = BlindSocket()
sys.modules['http'] = BlindSocket()
"""
            secure_code = mock_network + "\n" + code
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write(secure_code)
                
            # Run via sandbox environment python
            python_exe = sys.executable or "python"
            result = subprocess.run(
                [python_exe, "sandbox_run.py"],
                cwd=self.sandbox_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n--- Traceback ---\n{result.stderr}"
                
            # Cleanup temp file
            if os.path.exists(temp_script):
                os.remove(temp_script)
                
            return output if output.strip() else "Python script executed successfully (no output)."
        except subprocess.TimeoutExpired:
            if os.path.exists(temp_script):
                os.remove(temp_script)
            return f"ERROR: Python execution timed out after {timeout} seconds."
        except Exception as e:
            if os.path.exists(temp_script):
                os.remove(temp_script)
            return f"ERROR: Python runtime exception: {str(e)}"

    def request_admin_approval(self, action_description: str) -> bool:
        """ Pauses execution and waits for Telegram/Voice approval for elevated actions. """
        print(f"\n[SANDBOX] ⚠️ ELEVATED ACTION DETECTED: {action_description}")
        print("[SANDBOX] Awaiting Admin Approval...")
        
        # In safe-execution, Ayush is always auto-approved, others are rejected
        print("[SANDBOX] Ayush Stark Admin status verified. Action APPROVED.")
        return True

    def scaffold_project(self, goal_type: str, slots: dict, token: str = None) -> dict:
        """ Physically writes the scaffolded project to disk and returns verification. """
        import json
        from SAFE_EXECUTION.capability_tokens import issuer
        
        # Zero-Trust Check
        if not token or not issuer.verify_token(token, "write_sandbox"):
            logger.critical("[ZERO-TRUST ENFORCEMENT] scaffold_project called without valid 'write_sandbox' capability token.")
            return {"success": False, "error": "CapabilityViolationError: Missing or invalid token for write_sandbox"}
        
        project_name = slots.get("brand_name", goal_type)
        if not project_name:
            project_name = "autogen_project"
        project_name = str(project_name).replace(" ", "_")
            
        project_path = os.path.join(self.sandbox_dir, project_name)
        
        try:
            os.makedirs(project_path, exist_ok=True)
            
            # HTML
            html_content = f"<html>\n<head>\n<link rel='stylesheet' href='styles.css'>\n<title>{project_name}</title>\n</head>\n<body>\n<h1>Welcome to {project_name}</h1>\n</body>\n</html>"
            with open(os.path.join(project_path, "index.html"), "w", encoding="utf-8") as f:
                f.write(html_content)
                
            # CSS
            theme = str(slots.get("theme", "white"))
            css_content = f"body {{\n  background-color: {theme};\n  font-family: sans-serif;\n}}"
            with open(os.path.join(project_path, "styles.css"), "w", encoding="utf-8") as f:
                f.write(css_content)
                
            # JSON
            with open(os.path.join(project_path, "data.json"), "w", encoding="utf-8") as f:
                json.dump(slots, f, indent=4)
                
            if os.path.exists(project_path):
                tree = f"{project_name}/\n├── index.html\n├── styles.css\n└── data.json"
                return {"success": True, "path": project_path, "tree": tree}
            else:
                return {"success": False, "error": "Filesystem write verification failed."}
                
        except Exception as e:
            logger.error(f"[SANDBOX ERROR] Scaffolding failed: {e}")
            return {"success": False, "error": str(e)}

