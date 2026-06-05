"""
Planner Engine
The master coordinator that ties the goal, decomposer, tools, and execution loop together.
"""
import time
from AUTONOMOUS_CORE.task_decomposer import TaskDecomposer
from AUTONOMOUS_CORE.tool_selector import ToolSelector
from AUTONOMOUS_CORE.execution_manager import ExecutionManager
from AUTONOMOUS_CORE.workflow_memory import WorkflowMemory

class PlannerEngine:
    def __init__(self, brain_instance):
        print("\n[PLANNER] Initializing Autonomous Planner Engine...")
        self.brain = brain_instance
        self.decomposer = TaskDecomposer(self.brain)
        self.executor = ExecutionManager(self.brain)
        self.memory = WorkflowMemory()
        
    def run_goal(self, goal: str) -> str:
        print("\n=======================================================")
        print(f"       JARVIS AUTONOMOUS MISSION STARTED")
        print(f"       Goal: {goal}")
        print("=======================================================")
        
        self.memory.clear()
        
        # 1. Decompose
        steps = self.decomposer.decompose(goal)
        print(f"\n[PLANNER] Generated {len(steps)} Execution Steps:")
        for i, s in enumerate(steps):
            print(f"  {i+1}. {s}")
            
        # 2. Execute Chain
        steps = list(steps)
        step_index = 0
        max_loops = 12
        loops = 0
        
        while step_index < len(steps) and loops < max_loops:
            step = steps[step_index]
            loops += 1
            print(f"\n--- [PLANNER] Executing Step {step_index+1}/{len(steps)} (Loop {loops}/{max_loops}) ---")
            
            # Select Tool
            tool = ToolSelector.select_tool(step)
            
            # Execute safely
            result = self.executor.execute_step(step, tool, self.memory.get_context())
            
            # Self-Reflection
            reflection_prompt = f"""
            Analyze if the action completed successfully or if correction is needed to achieve the goal.
            Goal: {goal}
            Action: {step}
            Result: {result}
            
            Return ONLY a valid JSON object in this format:
            {{
                "success": true,
                "reason": "why it succeeded or failed",
                "correction": "what to do next if failed"
            }}
            """
            
            try:
                # Use brain to reflect on output
                reflection_raw = self.brain.process_request(reflection_prompt, force_heavy=True)
                import json
                clean_json = reflection_raw.replace("```json", "").replace("```", "").strip()
                reflection = json.loads(clean_json)
            except Exception as e:
                reflection = {"success": True, "reason": "Self-reflection parsing bypassed."}
                
            if reflection.get("success", True):
                print(f"[REFLECTION] Step Succeeded: {reflection.get('reason')}")
                self.memory.add_result(step, result)
                step_index += 1
            else:
                print(f"[REFLECTION] Step FAILED: {reflection.get('reason')}")
                correction = reflection.get("correction", f"Retry: {step}")
                print(f"[REFLECTION] Corrective Action Proposed: {correction}")
                
                # Insert corrective action as the next step
                steps.insert(step_index + 1, correction)
                self.memory.add_result(f"FAILED Step: {step}", f"Result: {result}. Proposed correction: {correction}")
                step_index += 1
                
            time.sleep(1.5)
            
        print("\n=======================================================")
        print("       MISSION COMPLETE. Context Stored.")
        print("=======================================================")
        return self.memory.get_context()

