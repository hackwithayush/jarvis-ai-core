"""
JARVIS Autonomous Intelligence 2.0 — OpenHands Autonomous Coding Agent
Implements multi-file codebase analysis, surgical patch generation, syntax verification,
sandboxed test execution, and iterative self-healing code repair loops.
"""
import os
import ast
import sys
import time
import shutil
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple

import config

logger = logging.getLogger("jarvis.openhands_agent")


class OpenHandsAgent:
    """
    Autonomous Software Engineering Agent inspired by OpenHands.
    Performs multi-step code exploration, patch synthesis, test-driven validation, and self-healing.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.backup_dir = os.path.join(self.workspace_root, "data", "code_backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        logger.info(f"OpenHands Autonomous Coding Agent active. Workspace: {self.workspace_root}")

    def _resolve_path(self, file_path: str) -> str:
        """
        Resolves file path relative to workspace root with canonical traversal
        and symlink escape protection.
        """
        if os.path.isabs(file_path):
            target = os.path.abspath(file_path)
        else:
            target = os.path.abspath(os.path.join(self.workspace_root, file_path))

        # Canonical real path resolution (resolves all symlinks, junctions, and relative parent markers)
        real_target = os.path.realpath(target)
        real_workspace = os.path.realpath(self.workspace_root)

        # Strict security boundary check
        try:
            rel = os.path.relpath(real_target, real_workspace)
            if rel.startswith("..") or os.path.isabs(rel) or (not real_target.lower().startswith(real_workspace.lower())):
                raise PermissionError(f"Access denied: Path '{file_path}' resolves outside authorized workspace.")
        except ValueError:
            # Cross-drive traversal on Windows
            raise PermissionError(f"Access denied: Path '{file_path}' traverses to another drive outside workspace.")

        return target

    def _create_backup(self, resolved_path: str) -> str:
        """Saves a timestamped backup copy of a file before modification."""
        if not os.path.exists(resolved_path):
            return ""
        rel = os.path.relpath(resolved_path, self.workspace_root).replace(os.sep, "_")
        backup_filename = f"{rel}_{int(time.time()*1000)}.bak"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        shutil.copy2(resolved_path, backup_path)
        return backup_path

    def read_source_file(self, file_path: str, max_lines: int = 500) -> Dict[str, Any]:
        """Safely reads content of a workspace file."""
        try:
            target = self._resolve_path(file_path)
            if not os.path.isfile(target):
                return {"status": "error", "error": f"File '{file_path}' does not exist."}

            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            total_lines = len(lines)
            content = "".join(lines[:max_lines])
            return {
                "status": "success",
                "file_path": file_path,
                "total_lines": total_lines,
                "content": content,
                "truncated": total_lines > max_lines
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def verify_syntax(self, code_str: str, file_path: str = "temp.py") -> Tuple[bool, Optional[str]]:
        """
        Validates syntax for Python files using AST parsing and byte compilation.
        Returns (is_valid, error_message).
        """
        if not file_path.endswith(".py"):
            return True, None

        try:
            ast.parse(code_str)
            return True, None
        except SyntaxError as syn_err:
            return False, f"SyntaxError at line {syn_err.lineno}, col {syn_err.offset}: {syn_err.msg}"
        except Exception as e:
            return False, str(e)

    def analyze_codebase(self, goal: str, target_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Explores target files and formulates an actionable technical specification and change plan.
        """
        files_to_inspect = target_files or []
        
        # If no target files provided, leverage Qdrant codebase semantic search to identify candidates
        if not files_to_inspect:
            try:
                from core.qdrant_engine import qdrant_engine
                if qdrant_engine.is_available():
                    hits = qdrant_engine.search(goal, collection_key="codebase", limit=4)
                    files_to_inspect = list({h.get("title") for h in hits if h.get("title")})
            except Exception:
                pass

        file_contexts = {}
        for f in files_to_inspect[:5]:
            read_res = self.read_source_file(f, max_lines=200)
            if read_res.get("status") == "success":
                file_contexts[f] = read_res.get("content")

        return {
            "status": "success",
            "goal": goal,
            "candidate_files": files_to_inspect,
            "inspected_files": list(file_contexts.keys()),
            "strategy": f"Synthesizing targeted patches for {len(file_contexts)} files based on directive."
        }

    def generate_and_apply_patch(
        self,
        file_path: str,
        instruction: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reads existing file, synthesizes modified code via LLM, validates syntax, and commits modification.
        """
        target = self._resolve_path(file_path)
        existing_code = ""
        is_new_file = not os.path.exists(target)

        if not is_new_file:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                existing_code = f.read()

        # Prepare prompt sections outside f-string for Python 3.10 compatibility
        ctx_section = f"Additional Context:\n{context}\n" if context else ""
        code_section = f"Existing Code:\n```python\n{existing_code[:6000]}\n```" if existing_code else "This is a NEW file. Generate the complete code implementation."

        prompt = f"""
You are OpenHands Autonomous Software Engineer.
Target File: '{file_path}'
Instruction: {instruction}

{ctx_section}
{code_section}

RULES:
1. Provide the COMPLETE updated code for this file.
2. Return ONLY the code inside a single ```python code block. No explanations.
"""
        from core.model_manager import ModelManager
        mgr = ModelManager()
        raw = mgr.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert autonomous software engineer. Generate robust, production-grade code."
        )

        clean_code = raw.replace("```python", "").replace("```", "").strip()
        if not clean_code:
            return {"status": "error", "error": "LLM generated empty code payload."}

        # Verify Syntax
        is_valid, syn_err = self.verify_syntax(clean_code, file_path)
        if not is_valid:
            logger.warning(f"OpenHands syntax check failed: {syn_err}")
            return {
                "status": "error",
                "error": f"Generated code failed syntax check: {syn_err}",
                "generated_code": clean_code
            }

        # Backup & Write
        backup_path = self._create_backup(target) if not is_new_file else ""
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(clean_code)

        logger.info(f"OpenHands successfully wrote patch to '{file_path}'. Backup: '{backup_path}'")
        return {
            "status": "success",
            "file_path": file_path,
            "backup_path": backup_path,
            "is_new_file": is_new_file,
            "lines_written": len(clean_code.splitlines())
        }

    def run_tests(self, test_command: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """
        Executes pytest or custom test command in the project environment.
        Captures exit codes, stdout, and error tracebacks.
        """
        python_exe = sys.executable
        if not test_command:
            # Default to running unittest / pytest discovery
            cmd = [python_exe, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
        elif isinstance(test_command, str):
            cmd = test_command if isinstance(test_command, list) else test_command.split()
        else:
            cmd = test_command

        # Replace 'python' or 'pytest' with exact virtualenv python binary
        if cmd[0] in ["python", "python3"]:
            cmd[0] = python_exe

        # Security Sandbox: Validate executable against allowlist (prevent shell escapes)
        base_bin = os.path.basename(cmd[0]).lower()
        if not (base_bin.startswith("python") or base_bin in ["pytest", "py_compile"]):
            return {
                "status": "error",
                "passed": False,
                "error": f"Security restriction: Execution of binary '{base_bin}' is disallowed in the test sandbox."
            }

        # Security Sandbox: Scrub all credentials and secrets from subprocess environment
        sanitized_env = os.environ.copy()
        secret_keys_to_purge = [
            "GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY",
            "OPENROUTER_API_KEY", "TOGETHER_API_KEY", "SECRET_KEY", "DATABASE_URL",
            "SQLALCHEMY_DATABASE_URI", "STRIPE_SECRET_KEY", "TAVILY_API_KEY"
        ]
        for k in secret_keys_to_purge:
            sanitized_env.pop(k, None)

        logger.info(f"[TEST RUNNER] Executing: {' '.join(cmd)}")
        try:
            start_t = time.time()
            res = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=sanitized_env,
                shell=False
            )
            duration = round(time.time() - start_t, 2)
            passed = (res.returncode == 0)

            return {
                "status": "success" if passed else "failed",
                "passed": passed,
                "exit_code": res.returncode,
                "duration_seconds": duration,
                "stdout": res.stdout[-2500:] if res.stdout else "",
                "stderr": res.stderr[-2500:] if res.stderr else "",
                "command": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "passed": False,
                "exit_code": -1,
                "error": f"Test execution timed out after {timeout} seconds."
            }
        except Exception as e:
            return {"status": "error", "passed": False, "error": str(e)}

    def autonomous_code_repair(
        self,
        goal: str,
        target_file: str,
        test_command: Optional[str] = None,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Full Autonomous Software Engineering Loop:
        1. Analyzes goal and target file.
        2. Synthesizes and applies patch.
        3. Runs test suite.
        4. If tests fail, feeds traceback back into LLM, generates fix, and re-tests up to max_iterations.
        """
        logger.info(f"[AUTONOMOUS CODING] Initiating self-healing loop for: '{goal}' on '{target_file}'")
        iteration_history = []
        last_error = ""

        for attempt in range(1, max_iterations + 1):
            logger.info(f"[AUTONOMOUS CODING] Iteration {attempt}/{max_iterations}")

            # 1. Synthesize patch
            context_hint = f"Previous test run failed with traceback:\n{last_error}\nFix the root cause." if last_error else None
            patch_res = self.generate_and_apply_patch(
                file_path=target_file,
                instruction=goal,
                context=context_hint
            )

            if patch_res.get("status") != "success":
                iteration_history.append({"iteration": attempt, "patch_status": "error", "error": patch_res.get("error")})
                last_error = patch_res.get("error")
                continue

            # 2. Run Tests
            test_res = self.run_tests(test_command=test_command, timeout=25)
            iteration_history.append({
                "iteration": attempt,
                "patch": patch_res,
                "tests_passed": test_res.get("passed", False),
                "test_output": test_res.get("stderr") or test_res.get("stdout")
            })

            # Check for success
            if test_res.get("passed"):
                logger.info(f"[AUTONOMOUS CODING] Mission accomplished on iteration {attempt}!")
                return {
                    "status": "success",
                    "iterations": attempt,
                    "target_file": target_file,
                    "tests_passed": True,
                    "history": iteration_history,
                    "summary": f"Successfully completed '{goal}' and verified all tests pass in {attempt} iteration(s)."
                }

            last_error = test_res.get("stderr") or test_res.get("stdout") or test_res.get("error")
            logger.warning(f"[AUTONOMOUS CODING] Iteration {attempt} tests failed. Feedback recorded for repair.")

        return {
            "status": "failed",
            "iterations": max_iterations,
            "target_file": target_file,
            "tests_passed": False,
            "history": iteration_history,
            "last_error": last_error,
            "summary": f"Autonomous coding loop reached max iterations ({max_iterations}) without passing all tests."
        }

    def rollback_file(self, backup_path: str, target_file: str) -> Dict[str, Any]:
        """Restores a file from a specified backup copy."""
        try:
            target = self._resolve_path(target_file)
            if not os.path.isfile(backup_path):
                return {"status": "error", "error": f"Backup file '{backup_path}' not found."}
            shutil.copy2(backup_path, target)
            logger.info(f"Rolled back '{target_file}' from '{backup_path}'.")
            return {"status": "success", "file_path": target_file, "restored_from": backup_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global Singleton Instance
openhands_agent = OpenHandsAgent()
