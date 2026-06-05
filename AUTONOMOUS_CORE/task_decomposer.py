"""
Task Decomposer
Breaks a high-level goal into actionable, sequential steps using the reasoning LLM.
"""
import json

class TaskDecomposer:
    def __init__(self, brain_instance):
        self.brain = brain_instance
        
    def decompose(self, goal: str) -> list:
        print(f"[DECOMPOSER] Breaking down goal using DeepSeek-R1...")
        prompt = f"""
        Break down this goal into a strict sequence of logical steps.
        Goal: {goal}
        Return ONLY a valid JSON list of strings representing the steps. 
        Example: ["search web for AI news", "summarize the top 3 articles", "send summary to telegram"]
        """
        response = self.brain.process_request(prompt, force_heavy=True)
        
        # Parse JSON reliably
        try:
            clean_json = response.replace("```json", "").replace("```", "").strip()
            steps = json.loads(clean_json)
            return steps
        except Exception as e:
            print(f"[DECOMPOSER ERROR] Failed to parse JSON steps: {e}")
            # Fallback to a single step if parsing fails
            return [f"Execute task: {goal}"]
