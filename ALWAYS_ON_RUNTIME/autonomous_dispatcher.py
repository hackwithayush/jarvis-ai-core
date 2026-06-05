"""
Autonomous Dispatcher
Receives voice commands, checks for interrupts, and passes goals to the Planner.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from AUTONOMOUS_CORE.planner_engine import PlannerEngine
from ALWAYS_ON_RUNTIME.active_task_queue import TaskState

class AutonomousDispatcher:
    def __init__(self, task_queue, brain_instance):
        self.queue = task_queue
        self.planner = PlannerEngine(brain_instance)
        
    def dispatch(self, text_input: str):
        # 1. Check for global interrupts
        interrupt_keywords = ["stop", "cancel task", "abort", "shut up", "pause", "cancel"]
        if any(kw in text_input.lower() for kw in interrupt_keywords):
            self.queue.trigger_interrupt()
            return "Task cancelled as requested."
            
        # 2. Dispatch to Planner
        self.queue.clear_interrupt()
        self.queue.set_state(TaskState.THINKING)
        
        # Execute goal via autonomous planner
        print(f"[DISPATCHER] Routing Goal to Autonomous Core: '{text_input}'")
        self.queue.set_state(TaskState.EXECUTING)
        
        result = self.planner.run_goal(text_input)
        
        # If interrupted mid-execution (assuming the executor eventually respects the flag)
        if self.queue.interrupt_flag:
            return "Task was aborted mid-execution."
            
        return result
