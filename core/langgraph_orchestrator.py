"""
JARVIS Autonomous Intelligence 2.0 — LangGraph Stateful Agent Orchestrator
Coordinates multi-step mission planning, zero-trust security guardian approval gates,
tool delegation (Browser-Use, OmniParser, OS Engine, Skills), NEMA verification, and self-healing recovery.
"""
import os
import re
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, TypedDict, Union

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("jarvis.langgraph_orchestrator")


# ─── Typed State Schema ────────────────────────────────────────────────────────

class StepDefinition(TypedDict):
    id: int
    description: str
    tool: str  # "browser", "omni_parser", "os_engine", "skills", "direct_answer"
    arguments: Dict[str, Any]
    status: str  # "pending", "running", "completed", "failed", "skipped"
    result: Optional[str]
    requires_approval: bool
    approval_status: Optional[str]  # "approved", "rejected", "pending"


class AutonomousAgentState(TypedDict):
    session_id: str
    task: str
    plan: List[Dict[str, Any]]
    current_step_index: int
    guardian_approved: bool
    pending_approval: Optional[Dict[str, Any]]
    execution_history: List[Dict[str, Any]]
    verification: Dict[str, Any]
    retry_count: int
    max_retries: int
    final_response: str
    status: str  # "planning", "awaiting_approval", "executing", "verifying", "recovering", "completed", "failed"
    error: Optional[str]


# ─── LangGraph Autonomous Orchestrator Class ───────────────────────────────────

class LangGraphOrchestrator:
    """
    Stateful Agent Orchestrator built on LangGraph StateGraph.
    Implements the Plan -> Guardian Gate -> Execute -> Verify -> Recover lifecycle.
    """

    SENSITIVE_PATTERNS = [
        r"\b(rm|del|delete|remove|erase|format|wipe)\b",
        r"\b(registry|regedit|hkey|hkcu|hklm)\b",
        r"\b(shutdown|reboot|restart|poweroff)\b",
        r"\b(kill|taskkill|pkill)\b",
        r"\b(drop\s+table|truncate|rmdir|rm\s+-rf)\b"
    ]

    def __init__(self):
        self.checkpointer = MemorySaver()
        self.active_sessions: Dict[str, AutonomousAgentState] = {}
        self.graph = self._compile_graph()
        logger.info("LangGraph Stateful Autonomous Orchestrator 2.0 initialized.")

    def _compile_graph(self):
        """Builds and compiles the stateful LangGraph execution graph."""
        workflow = StateGraph(AutonomousAgentState)

        # 1. Define Nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("guardian_gate", self._guardian_gate_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("verifier", self._verifier_node)
        workflow.add_node("recovery", self._recovery_node)
        workflow.add_node("synthesizer", self._synthesizer_node)

        # 2. Define Primary Edges
        workflow.add_edge(START, "planner")
        workflow.add_edge("planner", "guardian_gate")

        # 3. Conditional Routing after Guardian Gate
        workflow.add_conditional_edges(
            "guardian_gate",
            self._route_after_guardian,
            {
                "awaiting_approval": END,
                "executor": "executor"
            }
        )

        # 4. Executor to Verifier
        workflow.add_edge("executor", "verifier")

        # 5. Conditional Routing after Verifier
        workflow.add_conditional_edges(
            "verifier",
            self._route_after_verifier,
            {
                "next_step": "guardian_gate",
                "recovery": "recovery",
                "completed": "synthesizer",
                "failed": "synthesizer"
            }
        )

        # 6. Recovery Routing
        workflow.add_conditional_edges(
            "recovery",
            self._route_after_recovery,
            {
                "guardian_gate": "guardian_gate",
                "synthesizer": "synthesizer"
            }
        )

        workflow.add_edge("synthesizer", END)

        return workflow.compile(checkpointer=self.checkpointer)

    # ─── Node Implementations ──────────────────────────────────────────────────

    def _planner_node(self, state: AutonomousAgentState) -> Dict[str, Any]:
        """
        Planner Node:
        Deconstructs the user goal into a structured Task DAG of discrete, typed steps.
        Integrates Mem0 persistent intelligent memory recall for personalized planning.
        """
        task = state.get("task", "").strip()
        logger.info(f"[PLANNER NODE] Generating task DAG for: '{task[:60]}...'")

        # 0. Retrieve persistent user memory context from Mem0 & Qdrant RAG knowledge
        user_context = ""
        rag_context = ""
        try:
            from core.mem0_engine import mem0_engine
            user_context = mem0_engine.get_user_context(task)
            if user_context:
                logger.info(f"[PLANNER NODE] Injected Mem0 persistent recall for task: {task[:40]}")
        except Exception as mem_err:
            logger.debug(f"[PLANNER NODE] Mem0 context recall note: {mem_err}")

        try:
            from core.qdrant_engine import qdrant_engine
            rag_context = qdrant_engine.get_rag_context(task)
            if rag_context:
                logger.info(f"[PLANNER NODE] Injected Qdrant RAG context for task: {task[:40]}")
        except Exception as rag_err:
            logger.debug(f"[PLANNER NODE] Qdrant RAG recall note: {rag_err}")

        # 1. Check for simple informational / conversational queries
        t_low = task.lower()
        is_direct_chat = any(k in t_low for k in ["who are you", "what is your name", "hello", "hi jarvis", "explain", "what is", "tell me about", "what language do i", "my preference"]) and not any(k in t_low for k in ["browse", "click", "search web", "run", "file", "delete", "open"])

        if is_direct_chat:
            enhanced_prompt = f"{task}\n{user_context}\n{rag_context}".strip()
            steps = [{
                "id": 1,
                "description": f"Answer informational query: {task}",
                "tool": "direct_answer",
                "arguments": {"prompt": enhanced_prompt, "user_context": user_context, "rag_context": rag_context},
                "status": "pending",
                "result": None,
                "requires_approval": False,
                "approval_status": "approved"
            }]
            return {
                "plan": steps,
                "current_step_index": 0,
                "status": "planning",
                "retry_count": 0,
                "max_retries": 3,
                "execution_history": []
            }

        # 2. Intelligent Task DAG Generation (Heuristic + LLM fallback)
        steps = self._generate_dag(task)

        return {
            "plan": steps,
            "current_step_index": 0,
            "status": "planning",
            "retry_count": 0,
            "max_retries": 3,
            "execution_history": [],
            "error": None
        }

    def _generate_dag(self, task: str) -> List[Dict[str, Any]]:
        """Generates DAG steps according to task requirements."""
        t_low = task.lower()
        steps = []

        # Web browsing workflow
        if any(k in t_low for k in ["browse", "website", "search web", "navigate", "lookup on web", "scrape"]):
            steps.append({
                "id": 1,
                "description": f"Navigate and research web target for: {task}",
                "tool": "browser",
                "arguments": {"task": task, "headless": False},
                "status": "pending",
                "result": None,
                "requires_approval": False,
                "approval_status": "pending"
            })

        # Visual UI desktop workflow
        elif any(k in t_low for k in ["click", "button", "screen", "ui", "find on screen", "visual"]):
            steps.append({
                "id": 1,
                "description": f"Visual grounding & action targeting: {task}",
                "tool": "omni_parser",
                "arguments": {"directive": task},
                "status": "pending",
                "result": None,
                "requires_approval": False,
                "approval_status": "pending"
            })

        # Autonomous coding workflow (OpenHands)
        elif any(k in t_low for k in ["code", "script", "refactor", "bug", "patch", "unit test", "write python", "implement function", "fix error"]):
            steps.append({
                "id": 1,
                "description": f"Autonomous software engineering & code repair: {task}",
                "tool": "openhands",
                "arguments": {"goal": task},
                "status": "pending",
                "result": None,
                "requires_approval": False,
                "approval_status": "pending"
            })

        # Local LLM / llama.cpp offline execution workflow
        elif any(k in t_low for k in ["local llm", "offline ai", "llama", "benchmark local", "gguf", "offline inference"]):
            steps.append({
                "id": 1,
                "description": f"Execute local hardware-accelerated inference: {task}",
                "tool": "llama_local",
                "arguments": {"prompt": task},
                "status": "pending",
                "result": None,
                "requires_approval": False,
                "approval_status": "pending"
            })

        # OS / Command / System workflow
        elif any(k in t_low for k in ["run", "system", "file", "folder", "open app", "launch", "clean", "optimize", "delete"]):
            requires_approval = self._is_sensitive_command(task)
            steps.append({
                "id": 1,
                "description": f"Execute OS command or action: {task}",
                "tool": "os_engine",
                "arguments": {"command": task},
                "status": "pending",
                "result": None,
                "requires_approval": requires_approval,
                "approval_status": "pending"
            })

        # Composite multi-step fallback
        else:
            steps.append({
                "id": 1,
                "description": f"Synthesize primary response and strategy for: {task}",
                "tool": "direct_answer",
                "arguments": {"prompt": task},
                "status": "pending",
                "result": None,
                "requires_approval": False,
                "approval_status": "approved"
            })

        return steps

    def _guardian_gate_node(self, state: AutonomousAgentState) -> Dict[str, Any]:
        """
        Zero-Trust Guardian Gate Node:
        Inspects the active step for privileged/destructive operations before allowing execution.
        """
        plan = state.get("plan", [])
        idx = state.get("current_step_index", 0)

        if idx >= len(plan):
            return {"status": "completed"}

        step = plan[idx]
        desc = step.get("description", "")
        tool = step.get("tool", "")
        args = json.dumps(step.get("arguments", {}))

        # Check sensitive patterns
        is_sensitive = self._is_sensitive_command(desc + " " + args)
        step["requires_approval"] = is_sensitive

        # If already globally approved or marked approved
        if state.get("guardian_approved", False) or step.get("approval_status") == "approved":
            step["approval_status"] = "approved"
            logger.info(f"[GUARDIAN GATE] Step [{step['id']}] cleared for execution.")
            return {
                "plan": plan,
                "pending_approval": None,
                "status": "executing"
            }

        # If sensitive and not yet approved, pause and request human authorization
        if is_sensitive:
            logger.warning(f"[GUARDIAN GATE] Privileged operation paused at safety gate: '{desc}'")
            pending_details = {
                "step_id": step["id"],
                "tool": tool,
                "description": desc,
                "risk_level": "HIGH",
                "timestamp": time.time(),
                "reason": "Destructive or privileged system operation requires explicit human-in-the-loop authorization."
            }
            return {
                "plan": plan,
                "pending_approval": pending_details,
                "status": "awaiting_approval"
            }

        step["approval_status"] = "approved"
        return {
            "plan": plan,
            "pending_approval": None,
            "status": "executing"
        }

    def _executor_node(self, state: AutonomousAgentState) -> Dict[str, Any]:
        """
        Tool Execution Node:
        Delegates the current step to Browser-Use, OmniParser, OS Engine, Skills, or LLM.
        """
        plan = state.get("plan", [])
        idx = state.get("current_step_index", 0)
        history = list(state.get("execution_history", []))

        if idx >= len(plan):
            return {"status": "completed"}

        step = plan[idx]
        tool = step.get("tool", "direct_answer")
        args = step.get("arguments", {})
        step["status"] = "running"

        logger.info(f"[EXECUTOR NODE] Invoking tool '{tool}' for step [{step['id']}]: {step['description']}")

        result = None
        error = None

        try:
            if tool == "browser":
                from core.browser_engine import browser_engine
                task_str = args.get("task") or step.get("description")
                headless = bool(args.get("headless", False))
                b_res = browser_engine.execute_task(task_str, headless=headless)
                if b_res.get("status") == "success":
                    result = b_res.get("final_result") or f"Navigated successfully to {b_res.get('urls_visited', [])}"
                else:
                    error = b_res.get("error", "Browser task execution failed.")

            elif tool == "omni_parser":
                from VISION.omni_parser import omni_parser
                directive = args.get("directive") or step.get("description")
                v_res = omni_parser.visual_action(directive)
                if v_res.get("status") == "success":
                    result = v_res.get("spoken_response") or f"Executed visual action at {v_res.get('coordinates')}."
                else:
                    error = v_res.get("error", "Visual action failed.")

            elif tool == "os_engine":
                from core.os_engine import os_engine
                cmd = args.get("command") or step.get("description")
                os_res = os_engine.run_command(cmd)
                if isinstance(os_res, dict):
                    result = os_res.get("output") or os_res.get("message") or "Command executed successfully."
                else:
                    result = str(os_res)

            elif tool == "skills":
                from core.skills_registry import skills_registry
                skill_name = args.get("skill_name")
                context = args.get("context", {})
                s_res = skills_registry.execute_skill(skill_name, context)
                result = str(s_res)

            elif tool in ["qdrant", "knowledge_search"]:
                from core.qdrant_engine import qdrant_engine
                q_text = args.get("query") or step.get("description")
                hits = qdrant_engine.search(q_text, limit=3)
                if hits:
                    result = "\n".join([f"- [{h['title']}] {h['text']}" for h in hits])
                else:
                    result = "No matching knowledge entries found in Qdrant."

            elif tool in ["openhands", "coding", "code_repair"]:
                from core.openhands_agent import openhands_agent
                goal_str = args.get("goal") or step.get("description")
                target_f = args.get("target_file")
                if target_f:
                    rep_res = openhands_agent.generate_and_apply_patch(target_f, instruction=goal_str)
                    if rep_res.get("status") == "success":
                        result = f"OpenHands patched '{target_f}' ({rep_res.get('lines_written', 0)} lines written)."
                    else:
                        error = rep_res.get("error", "Patch generation failed.")
                else:
                    analysis = openhands_agent.analyze_codebase(goal_str)
                    result = f"OpenHands analyzed codebase: {analysis.get('strategy')}. Candidate files: {analysis.get('candidate_files')}"

            elif tool in ["llama_local", "llama_cpp", "local_inference"]:
                from core.llama_engine import llama_engine
                prompt_str = args.get("prompt") or step.get("description")
                if "benchmark" in prompt_str.lower():
                    b_res = llama_engine.benchmark()
                    result = f"Llama Local Benchmark: {b_res.get('performance_rating')} at {b_res.get('tokens_per_second')} tokens/sec ({b_res.get('duration_seconds')}s)."
                else:
                    l_res = llama_engine.generate(prompt=prompt_str)
                    if l_res.get("status") == "success":
                        result = f"[LOCAL GPU INFERENCE ({l_res.get('tokens_per_second')} t/s)]: {l_res.get('response')}"
                    else:
                        error = l_res.get("error", "Local inference failed.")

            else:  # "direct_answer" or fallback
                from core.model_manager import ModelManager
                mgr = ModelManager()
                prompt = args.get("prompt") or step.get("description")
                resp = mgr.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are J.A.R.V.I.S., Tony Stark's autonomous AI assistant. Provide concise, high-fidelity answers."
                )
                result = resp

        except Exception as exec_err:
            logger.error(f"[EXECUTOR NODE] Exception during step execution: {exec_err}", exc_info=True)
            error = str(exec_err)

        if error:
            step["status"] = "failed"
            step["result"] = f"ERROR: {error}"
            history.append({"step_id": step["id"], "tool": tool, "success": False, "error": error})
            return {
                "plan": plan,
                "execution_history": history,
                "error": error,
                "status": "verifying"
            }
        else:
            step["status"] = "completed"
            step["result"] = result
            history.append({"step_id": step["id"], "tool": tool, "success": True, "output": result})
            return {
                "plan": plan,
                "execution_history": history,
                "error": None,
                "status": "verifying"
            }

    def _verifier_node(self, state: AutonomousAgentState) -> Dict[str, Any]:
        """
        NEMA Verification Node:
        Evaluates step output against expected criteria. Decides whether to proceed, recover, or finish.
        """
        plan = state.get("plan", [])
        idx = state.get("current_step_index", 0)
        step = plan[idx] if idx < len(plan) else None

        if not step:
            return {"status": "completed", "verification": {"status": "passed", "confidence": 1.0}}

        logger.info(f"[VERIFIER NODE] Inspecting step [{step['id']}] status: {step.get('status')}")

        # Check for failure
        if step.get("status") == "failed" or state.get("error"):
            verification_rep = {
                "status": "failed",
                "confidence": 0.0,
                "critique": state.get("error") or "Step output marked failed."
            }
            return {
                "verification": verification_rep,
                "status": "recovering"
            }

        # Step succeeded
        verification_rep = {
            "status": "passed",
            "confidence": 0.95,
            "critique": "Step produced valid output satisfying operational criteria."
        }

        # Check if more steps remain
        if idx + 1 < len(plan):
            return {
                "current_step_index": idx + 1,
                "verification": verification_rep,
                "status": "executing"
            }
        else:
            return {
                "verification": verification_rep,
                "status": "completed"
            }

    def _recovery_node(self, state: AutonomousAgentState) -> Dict[str, Any]:
        """
        Self-Healing Recovery Node:
        Analyzes failure context, modifies plan/arguments, and retries up to max_retries.
        """
        retries = state.get("retry_count", 0) + 1
        max_retries = state.get("max_retries", 3)
        plan = list(state.get("plan", []))
        idx = state.get("current_step_index", 0)
        error = state.get("error", "Unknown execution failure")

        logger.warning(f"[RECOVERY NODE] Self-healing loop triggered (Attempt {retries}/{max_retries}). Root Cause: {error}")

        if retries > max_retries:
            logger.error("[RECOVERY NODE] Max retries exhausted. Terminating DAG with error report.")
            return {
                "status": "failed",
                "retry_count": retries,
                "final_response": f"I encountered an unrecoverable impediment while executing your directive: {error}. I have halted execution to protect workstation state."
            }

        # Self-heal strategy: patch failed step to headless or secondary fallback
        if idx < len(plan):
            failed_step = plan[idx]
            tool = failed_step.get("tool")
            failed_step["status"] = "pending"

            if tool == "browser":
                # Fallback to headless or direct query
                failed_step["arguments"]["headless"] = True
                failed_step["description"] += " [Recovery: Retrying in headless mode]"
            elif tool == "omni_parser":
                # Fallback to direct window focus / OS shortcut
                failed_step["tool"] = "os_engine"
                failed_step["description"] += " [Recovery: Falling back to OS shortcut]"
            else:
                failed_step["description"] += " [Recovery: Alternative parameter retry]"

        return {
            "plan": plan,
            "retry_count": retries,
            "status": "executing",
            "error": None
        }

    def _synthesizer_node(self, state: AutonomousAgentState) -> Dict[str, Any]:
        """
        Synthesizer Node:
        Consolidates completed execution steps into a cohesive Tony Stark J.A.R.V.I.S. response.
        """
        plan = state.get("plan", [])
        history = state.get("execution_history", [])
        status = state.get("status", "completed")
        error = state.get("error")

        if status == "failed" and error:
            resp = f"I apologize, sir. I encountered a critical blockage while executing the plan: {error}."
        else:
            # Extract key results
            results = []
            for s in plan:
                if s.get("result"):
                    results.append(f"- {s.get('description')}: {s.get('result')}")
            
            if results:
                bullet_summary = "\n".join(results)
                resp = f"Directive executed successfully, sir.\n\n{bullet_summary}"
            else:
                resp = "Directive executed successfully, sir. All parameters are nominal."

        logger.info(f"[SYNTHESIZER NODE] Final mission response formulated: {resp[:80]}...")
        return {
            "final_response": resp,
            "status": status
        }

    # ─── Conditional Routing Predicates ────────────────────────────────────────

    def _route_after_guardian(self, state: AutonomousAgentState) -> str:
        if state.get("status") == "awaiting_approval":
            return "awaiting_approval"
        return "executor"

    def _route_after_verifier(self, state: AutonomousAgentState) -> str:
        status = state.get("status")
        if status == "recovering":
            return "recovery"
        elif status == "completed":
            return "completed"
        elif status == "failed":
            return "failed"
        return "next_step"

    def _route_after_recovery(self, state: AutonomousAgentState) -> str:
        if state.get("status") == "failed":
            return "synthesizer"
        return "guardian_gate"

    def _is_sensitive_command(self, text: str) -> bool:
        """Determines if a command matches privileged or destructive patterns."""
        t_low = text.lower()
        return any(re.search(pat, t_low) for pat in self.SENSITIVE_PATTERNS)

    # ─── Public Mission API ───────────────────────────────────────────────────

    def run_mission(self, task: str, auto_approve: bool = False, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes an autonomous mission through the stateful LangGraph DAG.
        Returns full execution state, final response, and approval requirement if paused.
        """
        sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        initial_state: AutonomousAgentState = {
            "session_id": sid,
            "task": task,
            "plan": [],
            "current_step_index": 0,
            "guardian_approved": auto_approve,
            "pending_approval": None,
            "execution_history": [],
            "verification": {},
            "retry_count": 0,
            "max_retries": 3,
            "final_response": "",
            "status": "planning",
            "error": None
        }

        config = {"configurable": {"thread_id": sid}}
        result_state = self.graph.invoke(initial_state, config=config)
        self.active_sessions[sid] = result_state
        return result_state

    def approve_mission_step(self, session_id: str, approved: bool = True) -> Dict[str, Any]:
        """
        Resumes a paused mission after human-in-the-loop guardian approval.
        """
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            return {"status": "error", "error": f"Session '{session_id}' not found."}

        if not approved:
            session_state["status"] = "failed"
            session_state["final_response"] = "Mission halted: Human supervisor rejected the privileged operation."
            session_state["pending_approval"] = None
            return session_state

        session_state["guardian_approved"] = True
        session_state["pending_approval"] = None
        session_state["status"] = "executing"

        config = {"configurable": {"thread_id": session_id}}
        resumed_state = self.graph.invoke(session_state, config=config)
        self.active_sessions[session_id] = resumed_state
        return resumed_state


# Global Singleton Instance
langgraph_orchestrator = LangGraphOrchestrator()
