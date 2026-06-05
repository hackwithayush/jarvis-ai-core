"""
Autonomous Debugger — JARVIS Self-Healing Loop
Project-wide health scanner and repair coordinator.
"""
import logging
import os
import time
from typing import List

logger = logging.getLogger(__name__)

class AutoDebugger:
    """
    Scans the project for runtime errors and coordinates 
    fixes using the DebugEngine and the Git Safety Grid.
    """

    def __init__(self, debug_engine):
        self.debug_engine = debug_engine
        logger.info("Auto-Debugger Node: Self-Healing Active.")

    def run_once(self):
        """
        Perform a single project-wide health scan and attempt repairs.
        """
        logger.info("Auto-Debugger: Scanning neural pathways...")
        
        # 1. Scan for files (focusing on core logic)
        files = self.debug_engine.scan_project()
        
        for file in files:
            # 2. Check for runtime errors or syntax issues
            logger.debug(f"Scanning file: {file}")
            error = self.debug_engine.run_file(file)

            if error:
                logger.warning(f"⚠️ Bug detected in {file}. Initiating repair protocol...")
                # 3. Request fix from DebugEngine
                self.debug_engine.debug_and_fix(file, error)
            
    def scan_project(self) -> List[str]:
        """Discovery of active mission files."""
        src_files = []
        # Focus on core app files to avoid scanning node_modules or env
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
