"""
Debug Engine — JARVIS Self-HEALING Node
Neural repair loop with AI-led bug fixing and validation.
"""
import logging
import os
import subprocess
from typing import List, Tuple

logger = logging.getLogger(__name__)

class DebugEngine:
    """
    Identifies, analyzes, and repairs software anomalies.
    Integrates Git Safety Grid and Validation Engine for robust self-healing.
    """

    def __init__(self, chat_engine, git_manager, test_engine):
        self.chat_engine = chat_engine
        self.git = git_manager
        self.tester = test_engine
        logger.info("Debug Engine: Intelligence repair node online.")

    def run_file(self, file_path: str) -> str:
        """
        Attempt to execute a Python file to detect runtime or syntax errors.
        Returns the error string if failed, otherwise empty.
        """
        try:
            # Check for syntax errors first
            result = subprocess.run(
                ["python", "-m", "py_compile", file_path],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return result.stderr

            # Optional: Perform a dry run or static analysis
            # For now, we mainly check for syntax/import errors to avoid destructive execution
            return ""
        except Exception as e:
            return str(e)

    def debug_and_fix(self, file: str, error: str):
        """
        Analyze a bug, generate an AI fix, and apply it with rollback safety.
        """
        logger.warning(f"⚠️ Bug found in {file}: {error[:100]}...")

        # 1. Backup current state (Safety First)
        self.git.commit_backup(f"Neural Backup: Pre-fix for {os.path.basename(file)}")

        # 2. Generate fix using High-Cognition Brain
        logger.info(f"Debug Node: Requesting neural fix for {file}...")
        prompt = (
            f"IDENTIFIED BUG in {file}:\n\n{error}\n\n"
            "INSTRUCTION: Analyze the error and return the COMPLETE, corrected Python file content. "
            "Output ONLY the code, no explanation or markdown formatting."
        )
        
        # Using chat_engine's specialized generation
        # Assuming chat_engine has a way to get full completion
        fix = self.chat_engine.generate_direct(prompt)

        if not fix or "error" in fix.lower():
            logger.error("Debug Node: Failed to generate a valid fix.")
            return False

        # 3. Apply the fix
        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(fix)
            logger.info(f"Debug Node: Applied AI fix to {file}.")
        except Exception as e:
            logger.error(f"Debug Node: Failed to write fix: {e}")
            self.git.rollback()
            return False

        # 4. Run Automated Health Audit (Validation)
        success, output = self.tester.run_tests()

        if success:
            logger.info(f"✅ Debug Node: Fix verified for {file}.")
            self.git.commit_backup(f"Neural Repair: {os.path.basename(file)} stabilized.")
            return True
        else:
            logger.error(f"❌ Debug Node: Fix failed validation. Rolling back...")
            logger.debug(f"Test Output: {output}")
            self.git.rollback()
            return False

    def scan_project(self) -> List[str]:
        """Discovery of active mission files."""
        # This is duplicated logic from AutoDebugger for internal use if needed
        # but AutoDebugger usually provides the list.
        src_files = []
        targets = ["core", "app.py", "main.py", "telegram_bot.py", "models.py"]
        for t in targets:
            full_path = os.path.join(os.getcwd(), t)
            if os.path.isfile(full_path):
                src_files.append(full_path)
            elif os.path.isdir(full_path):
                for root, dirs, filenames in os.walk(full_path):
                    for f in filenames:
                        if f.endswith(".py") and not f.startswith("__"):
                            src_files.append(os.path.join(root, f))
        return src_files
