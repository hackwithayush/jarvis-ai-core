"""
Git Operations Module — JARVIS Safety Grid
Automated version control for self-healing and code security.
"""
import subprocess
import logging
import os

logger = logging.getLogger(__name__)

class GitManager:
    """
    Manages automated git operations to protect the codebase 
    during autonomous editing and self-healing.
    """

    def commit_backup(self, message: str = "Neural Auto-Backup"):
        """Save a restoration point for the current state."""
        try:
            logger.info(f"Git Node: Commit started -> {message}")
            subprocess.run(["git", "add", "."], check=True)
            # Only commit if there are changes
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if result.stdout:
                subprocess.run(["git", "commit", "-m", message], check=True)
                logger.info("✅ Git Node: Backup point created.")
            else:
                logger.info("Git Node: No changes detected, skipping commit.")
        except Exception as e:
            logger.error(f"Git Node: Backup failure: {e}")

    def rollback(self):
        """Revert the codebase to the last known stable restoration point."""
        try:
            logger.warning("⚠️ Git Node: Critical Failure Detected. Performing Rollback...")
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=True)
            logger.info("✅ Git Node: Rollback Successful.")
        except Exception as e:
            logger.error(f"Git Node: Rollback Failure: {e}")
