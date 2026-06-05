import logging
from langchain_core.messages import HumanMessage
from core.tools import ToolEngine

logger = logging.getLogger("jarvis.workers.technical")

class TechnicalWorker:
    """Specialized Agent: Python Execution & Logical Computation."""
    
    def __init__(self):
        self.tool_engine = ToolEngine()

    async def run(self, state: dict):
        """Execute code or perform math."""
        task_type = state.get("task_type", "code")
        query = state.get("query", "")
        
        logger.info(f"Technical Worker: Executing {task_type} for '{query}'...")
        
        if task_type == "code":
            # Assume query contains info about the code to run
            # The master agent should have extracted the code or we do it here
            from langchain_groq import ChatGroq
            import os
            llm = ChatGroq(model_name="llama-3.1-70b-versatile", groq_api_key=os.getenv("GROQ_API_KEY"))
            
            code_prompt = f"Extract or write the Python code needed to solve this: {query}. Respond ONLY with the code."
            code_res = await llm.ainvoke(code_prompt)
            code = code_res.content.strip(" `\n")
            
            result = self.tool_engine.execute_python_code(code)
            return {
                "messages": [HumanMessage(content=f"Code Execution Result:\n{result}", name="TechnicalNode")],
                "code": code,
                "output": result
            }
        
        elif task_type == "math":
            result = self.tool_engine.calculate(query)
            return {
                "messages": [HumanMessage(content=f"Calculation Result: {result}", name="TechnicalNode")],
                "output": result
            }
        
        return {"error": "Invalid task type for Technical Node."}
