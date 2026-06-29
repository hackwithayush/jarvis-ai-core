import os
import sys
import logging
import requests
import sqlite3
import config
from typing import Dict, Any

logger = logging.getLogger("jarvis.diagnostics")

class DiagnosticNode:
    """Neural Pre-Flight: Ensures all system vitals are operational."""

    @staticmethod
    def check_environment() -> Dict[str, Any]:
        """Validate critical environment variables, paths, and neural grid components."""
        results = {"status": "healthy", "warnings": [], "errors": [], "details": {}}
        
        # 1. Path Verification
        required_paths = [config.DATA_DIR, config.CONVERSATION_DIR, config.VOICE_DIR, config.LOG_DIR]
        paths_ok = 0
        for path in required_paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    results["warnings"].append(f"Created missing directory: {os.path.basename(path)}")
                    paths_ok += 1
                except Exception as e:
                    results["errors"].append(f"Storage Breach: Cannot create {path} ({e})")
            else:
                paths_ok += 1
        results["details"]["storage"] = f"{paths_ok}/{len(required_paths)} Directories OK"
        
        # 2. USER_AGENT Check
        user_agent = os.environ.get("USER_AGENT")
        if not user_agent:
            results["warnings"].append("USER_AGENT environment variable is missing. Web requests may fail.")
            results["details"]["user_agent"] = "MISSING"
        else:
            results["details"]["user_agent"] = f"OK ({user_agent})"

        # 3. Connectivity Check (Flagship Node)
        if not config.GROQ_API_KEY and not config.OPENAI_API_KEY:
            results["warnings"].append("Cloud Acceleration Grid offline (No API Keys). Falling back to pure local mode.")
            results["details"]["api_keys"] = "OFFLINE"
        else:
            results["details"]["api_keys"] = "ACTIVE"
        
        # 4. Model Engine Check (Ollama)
        try:
            resp = requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=2)
            if resp.status_code != 200:
                msg = "Local Intelligence Node (Ollama) unreachable."
                if config.SERVER_MODE: results["warnings"].append(msg)
                else: results["errors"].append(msg)
                results["details"]["ollama"] = "ERROR"
            else:
                results["details"]["ollama"] = "ONLINE"
        except:
            msg = "Local Intelligence Node (Ollama) offline."
            if config.SERVER_MODE: results["warnings"].append(msg)
            else: results["errors"].append(msg)
            results["details"]["ollama"] = "OFFLINE"

        # 5. Database Integrity
        try:
            if config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
                db_path = config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
                conn.close()
                results["details"]["database"] = "SQLITE OK"
            else:
                results["warnings"].append("External Database: Skipping deep integrity audit (Postgres).")
                results["details"]["database"] = "POSTGRES UNVERIFIED"
        except Exception as e:
            results["errors"].append(f"Neural Memory Corrupted: {e}")
            results["details"]["database"] = "CORRUPTED"
            
        # 6. LangGraph / Multi-Agent Grid
        try:
            from core.chat_engine import GRAPH_STATUS
            if GRAPH_STATUS["enabled"]:
                results["details"]["langgraph"] = "ONLINE"
            else:
                results["details"]["langgraph"] = f"OFFLINE ({GRAPH_STATUS.get('reason', 'Unknown')})"
        except Exception as e:
            results["details"]["langgraph"] = f"ERROR ({e})"

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

    @staticmethod
    def print_cli_report():
        """Display a beautiful terminal status report."""
        print("\n" + "="*40)
        print(" JARVIS NEURAL GRID DIAGNOSTICS")
        print("="*40)
        
        results = DiagnosticNode.check_environment()
        details = results["details"]
        
        print(f"USER_AGENT  : {details.get('user_agent', 'N/A')}")
        print(f"API Keys    : {details.get('api_keys', 'N/A')}")
        print(f"Ollama      : {details.get('ollama', 'N/A')}")
        print(f"Database    : {details.get('database', 'N/A')}")
        print(f"Storage     : {details.get('storage', 'N/A')}")
        
        print("-" * 40)
        print(" MULTI-AGENT STACK")
        print("-" * 40)
        print(f"LangGraph   : {details.get('langgraph', 'N/A')}")
        
        print("\n========================================")
        status = results['status'].upper()
        if status == "HEALTHY":
            print(f" SYSTEM STATUS: [ {status} ] ")
        else:
            print(f" SYSTEM STATUS: [ {status} ] ")
            if results['errors']:
                print("\nERRORS:")
                for e in results['errors']: print(f" - {e}")
            if results['warnings']:
                print("\nWARNINGS:")
                for w in results['warnings']: print(f" - {w}")
        print("========================================\n")

if __name__ == "__main__":
    DiagnosticNode.print_cli_report()
