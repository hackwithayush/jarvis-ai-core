"""
Jarvis v15.0 — Capability-Based Permissions & Governance Engine (CBPGE)
Enforces fine-grained resource permission boundaries (read, write, execute)
based on host agent clearance levels and generates secure execution clearance tokens.
"""
import hashlib
import time
import logging
from typing import Dict, Set, Optional

logger = logging.getLogger("jarvis.policy_engine")

class PolicyEngine:
    """Governs capabilities and issues validation tokens for agent execution."""

    def __init__(self):
        # Define default capability sets for each clearance level
        self.clearance_policies: Dict[str, Set[str]] = {
            "LOW": {
                "filesystem.read",
                "telemetry.query"
            },
            "MEDIUM": {
                "filesystem.read",
                "telemetry.query",
                "filesystem.write",
                "memory.query"
            },
            "HIGH": {
                "filesystem.read",
                "telemetry.query",
                "filesystem.write",
                "memory.query",
                "registry.modify",
                "network.access"
            },
            "CRITICAL": {
                "filesystem.read",
                "telemetry.query",
                "filesystem.write",
                "memory.query",
                "registry.modify",
                "network.access",
                "process.execute"
            }
        }
        self._token_secret = "JARVIS_NEURAL_CLEARANCE_KEY_2026"
        self.issued_tokens: Dict[str, dict] = {} # token -> details

    def get_capabilities(self, clearance_level: str) -> Set[str]:
        """Returns the set of allowed capabilities for a given clearance level."""
        return self.clearance_policies.get(clearance_level.upper(), set())

    def verify_capability(self, clearance_level: str, capability: str) -> bool:
        """Checks if a specific clearance level supports the requested capability."""
        allowed = self.get_capabilities(clearance_level)
        return capability in allowed

    def issue_execution_token(self, agent_id: str, capability: str, clearance_level: str) -> Optional[str]:
        """
        Generates a secure, short-lived clearance token for a specific capability
        if the agent's clearance level permits it.
        """
        if not self.verify_capability(clearance_level, capability):
            logger.warning(f"[POLICY] Execution denied: Agent '{agent_id}' requested '{capability}' with '{clearance_level}' clearance.")
            return None

        # Generate a unique validation signature
        timestamp = time.time()
        raw_payload = f"{agent_id}:{capability}:{clearance_level}:{timestamp}:{self._token_secret}"
        token = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()[:16]

        self.issued_tokens[token] = {
            "agent_id": agent_id,
            "capability": capability,
            "clearance_level": clearance_level,
            "issued_at": timestamp,
            "expires_at": timestamp + 60, # 60 seconds TTL
            "used": False
        }
        
        logger.info(f"[POLICY] Issued clearance token '{token}' to Agent '{agent_id}' for '{capability}'")
        return token

    def validate_execution_token(self, token: str, capability: str) -> bool:
        """
        Validates if an execution token is genuine, matches the requested capability,
        and has not expired or been previously used.
        """
        if token not in self.issued_tokens:
            logger.error(f"[POLICY] Validation failed: Token '{token}' is invalid or unregistered.")
            return False

        details = self.issued_tokens[token]
        
        # Check expiration
        if time.time() > details["expires_at"]:
            logger.error(f"[POLICY] Validation failed: Token '{token}' has expired.")
            return False

        # Check capability match
        if details["capability"] != capability:
            logger.error(f"[POLICY] Validation failed: Token '{token}' was issued for '{details['capability']}', not '{capability}'.")
            return False

        # Check usage (one-time execution clearance)
        if details["used"]:
            logger.error(f"[POLICY] Validation failed: Token '{token}' was already consumed.")
            return False

        # Mark as used
        details["used"] = True
        logger.info(f"[POLICY] Successfully validated and consumed clearance token '{token}' for '{capability}'")
        return True

# Global singleton policy manager
policy_engine = PolicyEngine()
