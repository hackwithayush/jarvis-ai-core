"""
Cryptographic Capability-Token Architecture
Enforces zero-trust agent isolation via ephemeral HMAC signed tokens.
"""
import hmac
import hashlib
import json
import secrets
import logging
from typing import List, Dict

logger = logging.getLogger("jarvis.capability_tokens")

class TokenIssuer:
    def __init__(self):
        # Ephemeral secret key generated on boot. Tokens do not survive restarts.
        self._master_secret = secrets.token_hex(32).encode('utf-8')
        logger.info("[TOKEN ISSUER] Ephemeral master secret generated. Zero-Trust Enforcement Active.")
        
    def _sign_payload(self, payload_str: str) -> str:
        """Generates an HMAC-SHA256 signature for the payload."""
        return hmac.new(self._master_secret, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

    def mint_token(self, agent_id: str, scopes: List[str]) -> str:
        """
        Mints a cryptographic capability token for a specific agent.
        Scopes can include: 'read_sandbox', 'write_sandbox', 'execute_shell', 'invoke_firewall'
        """
        payload = {
            "agent_id": agent_id,
            "scopes": sorted(scopes)
        }
        payload_str = json.dumps(payload, separators=(',', ':'))
        signature = self._sign_payload(payload_str)
        
        token = {
            "payload": payload,
            "signature": signature
        }
        return json.dumps(token)
        
    def verify_token(self, token_str: str, required_scope: str) -> bool:
        """
        Verifies the cryptographic integrity of the token and checks if it holds the required scope.
        """
        try:
            token = json.loads(token_str)
            payload = token.get("payload", {})
            signature = token.get("signature", "")
            
            # Re-sign the payload to verify integrity
            payload_str = json.dumps(payload, separators=(',', ':'))
            expected_signature = self._sign_payload(payload_str)
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.critical(f"[SECURITY BREACH] Forged capability token detected for agent: {payload.get('agent_id', 'UNKNOWN')}")
                return False
                
            # Verify scope
            if required_scope not in payload.get("scopes", []):
                logger.error(f"[CAPABILITY DENIED] Agent '{payload.get('agent_id')}' attempted to use scope '{required_scope}' without authorization.")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"[TOKEN ERROR] Failed to parse or verify capability token: {e}")
            return False

# Global Issuer Instance
issuer = TokenIssuer()
