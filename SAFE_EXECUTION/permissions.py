"""
Autonomous Action Permissions
Controls granular capabilities for agent execution.
Implements Action Journaling and Execution Replay logging.
"""
import os
import json
import sqlite3
import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger("jarvis.permissions")

class PermissionManager:
    def __init__(self):
        # Master Schema
        self.capabilities = {
            "filesystem": "restricted",      # allowed, restricted, blocked
            "browser": "allowed",
            "terminal": "confirm_required",  # allowed, confirm_required, blocked
            "delete_operations": "blocked",
            "network": "allowed",
            "system_config": "blocked"
        }
        
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "action_journal.db"))
        self._init_db()
        logger.info("[PERMISSIONS] Action Permissions and Journaling initialized.")
        
    def _init_db(self):
        self.anchor_path = os.path.join(os.path.dirname(self.db_path), ".audit_anchor_key")
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    agent TEXT,
                    action_type TEXT,
                    payload TEXT,
                    status TEXT,
                    rollback_data TEXT
                )
            ''')
            try:
                cursor.execute("ALTER TABLE action_journal ADD COLUMN entry_hash TEXT")
            except sqlite3.OperationalError:
                pass # Column exists
            conn.commit()
            
            # PHASE 13: Audit Integrity Anchor Verification
            cursor.execute("SELECT entry_hash FROM action_journal ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            top_hash = row[0] if row and row[0] else "GENESIS_BLOCK"
            
            if os.path.exists(self.anchor_path):
                with open(self.anchor_path, "r") as f:
                    anchored_hash = f.read().strip()
                if anchored_hash != top_hash:
                    logger.critical(f"[SECURITY BREACH] FATAL: Audit Anchor Rollback Detected! DB Hash: {top_hash} != Anchor: {anchored_hash}")
                    raise RuntimeError("Audit Anchor Rollback Detected. System compromised.")
            else:
                with open(self.anchor_path, "w") as f:
                    f.write(top_hash)
            
            conn.close()
        except Exception as e:
            logger.error(f"[PERMISSIONS] Failed to initialize action journal: {e}")
            
    def check_permission(self, domain: str, action: str) -> bool:
        """Evaluates if a given domain action is permitted by the capability schema."""
        level = self.capabilities.get(domain, "blocked")
        
        if level == "blocked":
            logger.warning(f"[PERMISSIONS] Domain '{domain}' is blocked. Denying '{action}'.")
            return False
            
        if level == "restricted":
            # Heuristic restriction (e.g. no deletion or out-of-sandbox modification)
            if "delete" in action.lower() or "rm " in action.lower():
                logger.warning(f"[PERMISSIONS] Domain '{domain}' is restricted. Denying destructive '{action}'.")
                return False
                
        if level == "confirm_required":
            logger.info(f"[PERMISSIONS] Action '{action}' on '{domain}' requires explicit admin confirmation. Auto-denying in autonomous mode.")
            return False
            
        return True
        
    def log_action(self, agent: str, action_type: str, payload: str, status: str, rollback_data: str = "") -> int:
        """Saves an execution trace to the Action Journal for audit and replay."""
        import hashlib
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get previous hash
            cursor.execute("SELECT entry_hash FROM action_journal ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row[0] if row and row[0] else "GENESIS_BLOCK"
            
            timestamp = datetime.datetime.now().isoformat()
            hash_input = f"{prev_hash}{timestamp}{agent}{action_type}{payload}{status}".encode('utf-8')
            new_hash = hashlib.sha256(hash_input).hexdigest()
            
            cursor.execute(
                "INSERT INTO action_journal (timestamp, agent, action_type, payload, status, rollback_data, entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (timestamp, agent, action_type, payload, status, rollback_data, new_hash)
            )
            journal_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Update physical anchor
            with open(self.anchor_path, "w") as f:
                f.write(new_hash)
                
            return journal_id
        except Exception as e:
            logger.error(f"[PERMISSIONS] Failed to log action: {e}")
            return -1

# Global Instance
permissions = PermissionManager()
