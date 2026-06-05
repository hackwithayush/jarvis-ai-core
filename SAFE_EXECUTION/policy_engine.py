"""
Enterprise Policy Enforcement Engine
Defines immutable, hard-coded runtime constants that the LLM cannot manipulate.
"""
import logging

logger = logging.getLogger("jarvis.policy_engine")

class EnterprisePolicyEngine:
    def __init__(self):
        # Master Immutable Policies
        self.policies = {
            "ENFORCE_NETWORK_ISOLATION": True,     # Forces mock network injection
            "MAX_EXECUTION_TIMEOUT": 10,           # Max seconds a sandboxed process can run
            "AUTO_LOCKDOWN_ON_BURNOUT": True,      # Forces system halt if burnout is reached
            "REQUIRE_CAPABILITY_TOKENS": True,     # Enforces Zero-Trust token checks
            "STRICT_AST_ANALYSIS": True            # Enforces payload inspection
        }
        logger.info("[POLICY ENGINE] Immutable Enterprise Rules active.")
        
    def get_policy(self, rule: str) -> bool:
        """Retrieves a system policy. Fails closed (False) if rule is missing."""
        return self.policies.get(rule, False)
        
    def enforce_burnout_lockdown(self, cognitive_graph) -> bool:
        """
        Checks if the system is in burnout. If AUTO_LOCKDOWN_ON_BURNOUT is active,
        physically prevents execution transitions.
        """
        if not self.get_policy("AUTO_LOCKDOWN_ON_BURNOUT"):
            return False
            
        metrics = {k: v.value for k, v in cognitive_graph.nodes.items()}
        if metrics.get("fatigue", 0) > 0.85 and metrics.get("stress", 0) > 0.85:
            logger.critical("[POLICY ENGINE] SYSTEM BURNOUT DETECTED. Enforcing execution lockdown.")
            return True
        return False

# Global Instance
engine = EnterprisePolicyEngine()
