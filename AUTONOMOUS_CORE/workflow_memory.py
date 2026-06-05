"""
Workflow Memory
Maintains the context and history of an active execution chain so steps can share data.
"""
class WorkflowMemory:
    def __init__(self):
        self.history = []
        self.compiled_context = ""
        
    def add_result(self, step: str, result: str):
        self.history.append({"step": step, "result": result})
        # Keep context string continually updated for the LLM
        self.compiled_context += f"\n--- STEP COMPLETED ---\nAction: {step}\nResult: {result}\n"
        
    def get_context(self) -> str:
        return self.compiled_context
        
    def clear(self):
        self.history = []
        self.compiled_context = ""
