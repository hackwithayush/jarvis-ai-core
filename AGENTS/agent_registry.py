"""
Agent Registry
Central hub for specialized agents. Maps domains to specific expert routines.
"""
class BaseAgent:
    def __init__(self):
        self.capability_token = None
        
    def set_token(self, token: str):
        self.capability_token = token
        
    def execute(self, task: str):
        pass

class CodingAgent(BaseAgent):
    def execute(self, task: str):
        return f"[CODING AGENT] Debugging/Architecting code for: {task}"

class ResearchAgent(BaseAgent):
    def execute(self, task: str):
        return f"[RESEARCH AGENT] Compiling multi-source data and web reports for: {task}"

class GamingAgent(BaseAgent):
    def execute(self, task: str):
        return f"[GAMING AGENT] Optimizing FPS, PC state, and OBS hooks for: {task}"

class AutomationAgent(BaseAgent):
    def execute(self, task: str):
        return f"[AUTOMATION AGENT] Executing routine file/folder operations for: {task}"

from AGENTS.security_agent.guard_node import SecurityGuardAgent
from SAFE_EXECUTION.capability_tokens import issuer

AVAILABLE_AGENTS = {
    "coding": CodingAgent(),
    "research": ResearchAgent(),
    "gaming": GamingAgent(),
    "automation": AutomationAgent(),
    "security": SecurityGuardAgent()
}

class AgentRegistry:
    _tokens_issued = False
    
    @classmethod
    def _issue_tokens(cls):
        if cls._tokens_issued: return
        AVAILABLE_AGENTS["security"].set_token(issuer.mint_token("security_agent", ["read_sandbox", "invoke_firewall", "mutate_cognition"]))
        AVAILABLE_AGENTS["coding"].set_token(issuer.mint_token("coding_agent", ["read_sandbox", "write_sandbox", "execute_shell"]))
        AVAILABLE_AGENTS["research"].set_token(issuer.mint_token("research_agent", ["read_sandbox", "network"]))
        AVAILABLE_AGENTS["gaming"].set_token(issuer.mint_token("gaming_agent", ["read_sandbox"]))
        AVAILABLE_AGENTS["automation"].set_token(issuer.mint_token("automation_agent", ["read_sandbox", "write_sandbox"]))
        cls._tokens_issued = True

    @staticmethod
    def delegate(domain: str, task: str, model_manager=None) -> str:
        AgentRegistry._issue_tokens()
        domain = domain.lower()
        if domain in AVAILABLE_AGENTS:
            # PHASE 15: Removed print spam. Delegation is now silent and transparent.
            agent = AVAILABLE_AGENTS[domain]
            if domain == "security":
                return agent.execute(task, model_manager=model_manager)
            return agent.execute(task)
        return f"[REGISTRY ERROR] Specialized Agent '{domain}' not found in registry."
