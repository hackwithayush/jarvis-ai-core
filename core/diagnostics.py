import os
import logging
import requests
import sqlite3
import config

logger = logging.getLogger("jarvis.diagnostics")

class DiagnosticNode:
    """Neural Pre-Flight: Ensures all system vitals are operational."""

    @staticmethod
    def check_environment():
        """Validate critical environment variables and paths."""
        results = {"status": "healthy", "warnings": [], "errors": []}
        
        # 1. Path Verification
        required_paths = [config.DATA_DIR, config.CONVERSATION_DIR, config.VOICE_DIR, config.LOG_DIR]
        for path in required_paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    results["warnings"].append(f"Created missing directory: {os.path.basename(path)}")
                except Exception as e:
                    results["errors"].append(f"Storage Breach: Cannot create {path} ({e})")
        
        # 2. Connectivity Check (Flagship Node)
        if not config.GROQ_API_KEY and not config.OPENAI_API_KEY:
            results["warnings"].append("Cloud Acceleration Grid offline (No API Keys). Falling back to pure local mode.")
        
        # 3. Model Engine Check (Ollama)
        try:
            resp = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=2)
            if resp.status_code != 200:
                msg = "Local Intelligence Node (Ollama) unreachable."
                if config.SERVER_MODE: results["warnings"].append(msg)
                else: results["errors"].append(msg)
        except:
            msg = "Local Intelligence Node (Ollama) offline."
            if config.SERVER_MODE: results["warnings"].append(msg)
            else: results["errors"].append(msg)

        # 4. Database Integrity
        try:
            if config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
                db_path = config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
                conn.close()
            else:
                # Basic reachability check for external databases
                results["warnings"].append("External Database: Skipping deep integrity audit (Postgres).")
        except Exception as e:
            results["errors"].append(f"Neural Memory Corrupted: {e}")

        if results["errors"]:
            results["status"] = "critical"
        elif results["warnings"]:
            results["status"] = "degraded"
            
        return results

    @staticmethod
    def run_preflight():
        """Execute diagnostic sequence and log results."""
        logger.info("Initializing Neural Pre-Flight Sequence...")
        results = DiagnosticNode.check_environment()
        
        if results["status"] == "critical":
            logger.error(f"SYSTEM CRITICAL: {', '.join(results['errors'])}")
        elif results["status"] == "degraded":
            logger.warning(f"SYSTEM DEGRADED: {', '.join(results['warnings'])}")
        else:
            logger.info("SYSTEM HEALTHY: All neural nodes stable.")
            
        return results
