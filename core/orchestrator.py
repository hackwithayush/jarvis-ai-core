"""
True Multi-Agent Orchestrator
Coordinates specialized agents using confidence scoring, voting, and arbitration.
Agents: Planner, Vision, Memory, OS Control, and MCP External Extensions.
"""
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("jarvis.orchestrator")

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        
    def evaluate_confidence(self, task: str) -> float:
        """Returns a confidence score between 0.0 and 1.0 indicating how suited this agent is for the task."""
        return 0.0
        
    def execute(self, task: str) -> str:
        """Executes the task and returns the result."""
        raise NotImplementedError()

class VisionAgent(BaseAgent):
    def __init__(self):
        super().__init__("VisionAgent")
        
    def evaluate_confidence(self, task: str) -> float:
        t = task.lower()
        if any(keyword in t for keyword in ["see", "screen", "look", "read", "screenshot", "vision", "parse ui", "omniparser"]):
            return 0.95
        return 0.1
        
    def execute(self, task: str) -> str:
        try:
            from VISION.desktop_vision import DesktopVision
            t = task.lower()
            if any(k in t for k in ["parse", "elements", "boxes", "som", "where is", "find button", "find input"]):
                res = DesktopVision.omni_parse(task)
                total = res.get("total_elements", 0)
                plan = res.get("action_plan", {})
                return f"[OMNIPARSER RESPONSE] Grounded {total} UI elements on display. Plan: {plan.get('reason', 'Ready')}"
            else:
                res = DesktopVision.describe_screen_layout()
                return f"[VISION RESPONSE] {res}"
        except Exception as e:
            return f"Vision Agent Failed: {e}"

class ComputerControlAgentNode(BaseAgent):
    def __init__(self):
        super().__init__("ComputerControlAgent")
        
    def evaluate_confidence(self, task: str) -> float:
        t = task.lower()
        if any(keyword in t for keyword in ["click", "type", "mouse", "keyboard", "scroll", "press"]):
            return 0.90
        return 0.05
        
    def execute(self, task: str) -> str:
        try:
            from AUTONOMOUS_CORE.execution_manager import ExecutionManager
            # Mocking brain context for execution manager
            from core.brain import JarvisBrain
            em = ExecutionManager(JarvisBrain())
            res = em.execute_step(task, tool="computer_control", context="")
            return f"[AUTOMATION RESPONSE] {res}"
        except Exception as e:
            return f"Automation Agent Failed: {e}"

class PlannerAgentNode(BaseAgent):
    def __init__(self):
        super().__init__("PlannerAgent")
        
    def evaluate_confidence(self, task: str) -> float:
        """Planner handles complex, multi-step ambiguous goals."""
        t = task.lower()
        if any(keyword in t for keyword in ["build", "create", "find and", "mission", "goal", "research"]):
            return 0.85
        return 0.5 # Default fallback
        
    def execute(self, task: str) -> str:
        try:
            from AUTONOMOUS_CORE.planner_engine import PlannerEngine
            from core.brain import JarvisBrain
            planner = PlannerEngine(JarvisBrain())
            res = planner.run_goal(task)
            return f"[PLANNER RESPONSE]\n{res}"
        except Exception as e:
            return f"Planner Agent Failed: {e}"

class MCPExtensionAgent(BaseAgent):
    def __init__(self):
        super().__init__("MCPExtensionAgent")
        
    def evaluate_confidence(self, task: str) -> float:
        """
        Bids confidence if the task matches registered external MCP or dynamic plugins.
        """
        try:
            from core.plugin_sdk import plugin_registry
            t = task.lower()
            
            highest_bid = 0.0
            for name, info in plugin_registry.plugins.items():
                if name.lower() in t or any(word in t for word in name.lower().split("_")):
                    highest_bid = max(highest_bid, 0.90)
                description = info.get("description", "").lower()
                if description and any(word in t for word in description.split()):
                    highest_bid = max(highest_bid, 0.80)
            return highest_bid
        except Exception:
            return 0.0

    def execute(self, task: str) -> str:
        """
        Executes the best matching tool registered in the plugin registry.
        """
        try:
            from core.plugin_sdk import plugin_registry
            from core.model_manager import ModelManager
            import json
            
            t = task.lower()
            best_tool = None
            for name in plugin_registry.plugins.keys():
                if name.lower() in t:
                    best_tool = name
                    break
            
            if not best_tool:
                for name in plugin_registry.plugins.keys():
                    parts = name.lower().split("_")
                    action_words = [p for p in parts if p not in ["mock", "server", "plugin", "mcp"]]
                    if action_words and any(w in t for w in action_words):
                        best_tool = name
                        break
            
            if not best_tool:
                for name, info in plugin_registry.plugins.items():
                    desc = info.get("description", "").lower()
                    if desc and any(word in t for word in desc.split() if len(word) > 4):
                        best_tool = name
                        break
                        
            if not best_tool:
                if plugin_registry.plugins:
                    best_tool = list(plugin_registry.plugins.keys())[0]
                else:
                    return "Error: No external MCP tools registered."
                    
            tool_info = plugin_registry.plugins[best_tool]
            parameters_schema = tool_info.get("parameters", {"type": "object", "properties": {}})
            
            # Asynchronously parse arguments via LLM
            model_mgr = ModelManager()
            prompt = f"""
You are the JARVIS Argument Extraction Subsystem.
We want to invoke the tool '{best_tool}' with schema:
{json.dumps(parameters_schema, indent=2)}

Extract the arguments as a valid JSON dictionary based on the task description:
"{task}"

Return ONLY valid JSON.
"""
            raw_response = model_mgr.generate(messages=[{"role": "user", "content": prompt}], model="llama-3.1-8b-instant")
            clean = raw_response.replace("```json", "").replace("```", "").strip()
            arguments = json.loads(clean)
            if not isinstance(arguments, dict):
                arguments = {}
        except Exception as e:
            arguments = {}
            logger.error(f"[ORCHESTRATOR] Argument extraction failed: {e}")
            
        logger.info(f"[ORCHESTRATOR] Routing execution to tool '{best_tool}' with args: {arguments}")
        res = plugin_registry.execute_plugin(best_tool, arguments)
        return f"[MCP RESPONSE from {best_tool}]\n{res}"


class BrowserAgentNode(BaseAgent):
    def __init__(self):
        super().__init__("BrowserAgent")
        
    def evaluate_confidence(self, task: str) -> float:
        t = task.lower()
        if any(keyword in t for keyword in ["browse", "navigate to", "website", "web page", "scrape", "amazon", "login to", "fill form", "extract from web"]):
            return 0.92
        return 0.05
        
    def execute(self, task: str) -> str:
        try:
            from core.browser_engine import browser_engine
            res = browser_engine.execute_task(task, headless=False)
            if res.get("status") == "success":
                return f"[BROWSER RESPONSE] {res.get('final_result', 'Task completed.')}"
            else:
                return f"[BROWSER ERROR] {res.get('error', 'Execution failed.')}"
        except Exception as e:
            return f"Browser Agent Failed: {e}"

class MemoryAgentNode(BaseAgent):
    def __init__(self):
        super().__init__("MemoryAgent")

    def evaluate_confidence(self, task: str) -> float:
        t = task.lower()
        if any(k in t for k in ["remember", "what do you remember", "my preference", "do you know my", "recall", "favorite", "save to memory", "what language do i"]):
            return 0.94
        return 0.05

    def execute(self, task: str) -> str:
        try:
            from core.mem0_engine import mem0_engine
            t = task.lower()
            if any(k in t for k in ["remember that", "remember:", "save to memory", "my preference is", "my favorite"]):
                clean = re.sub(r"^(?:please\s+)?remember\s+(?:that\s+)?", "", task, flags=re.IGNORECASE).strip()
                res = mem0_engine.add_memory(clean)
                return f"[MEM0 MEMORY STORED] Stored in persistent memory: '{clean}'"
            else:
                memories = mem0_engine.search_memory(task)
                if memories:
                    facts = [f"- {m.get('memory', '')}" for m in memories if m.get('memory')]
                    return "[MEM0 RECALL]\n" + "\n".join(facts)
                return "[MEM0 RECALL] No matching persistent memories found for your query, sir."
        except Exception as e:
            return f"Memory Agent Failed: {e}"

class AgentOrchestrator:
    def __init__(self):
        self.agents: List[BaseAgent] = [
            VisionAgent(),
            BrowserAgentNode(),
            ComputerControlAgentNode(),
            PlannerAgentNode(),
            MemoryAgentNode(),
            MCPExtensionAgent()
        ]
        
    def arbitrate(self, task: str) -> BaseAgent:
        """Voting mechanism: Ask all agents for confidence score, pick the highest."""
        best_agent = None
        highest_score = -1.0
        
        for agent in self.agents:
            score = agent.evaluate_confidence(task)
            logger.debug(f"[ORCHESTRATOR] Agent '{agent.name}' bid: {score}")
            if score > highest_score:
                highest_score = score
                best_agent = agent
                
        # Confidence Threshold: Default fallback to Planner
        if highest_score < 0.3:
            logger.warning(f"[ORCHESTRATOR] Low confidence ({highest_score}). Defaulting to PlannerAgent.")
            return next(a for a in self.agents if a.name == "PlannerAgent")
            
        logger.info(f"[ORCHESTRATOR] Task '{task}' assigned to {best_agent.name} (Score: {highest_score})")
        return best_agent
        
    def dispatch(self, task: str) -> str:
        """Main entry point for handling an ambiguous command."""
        target_agent = self.arbitrate(task)
        return target_agent.execute(task)

    def run_autonomous_mission(self, task: str, auto_approve: bool = False, session_id: Optional[str] = None) -> Dict[str, Any]:
        """LangGraph Autonomous Intelligence 2.0: Multi-step DAG planning, verification, and recovery."""
        from core.langgraph_orchestrator import langgraph_orchestrator
        return langgraph_orchestrator.run_mission(task=task, auto_approve=auto_approve, session_id=session_id)

    def approve_mission(self, session_id: str, approved: bool = True) -> Dict[str, Any]:
        """Resumes a paused mission after security guardian human-in-the-loop approval."""
        from core.langgraph_orchestrator import langgraph_orchestrator
        return langgraph_orchestrator.approve_mission_step(session_id=session_id, approved=approved)

# Global Orchestrator Instance
orchestrator = AgentOrchestrator()
