"""
Tool Selector
Determines which tool or module to use for a specific sub-task.
"""
class ToolSelector:
    @staticmethod
    def select_tool(step_description: str) -> str:
        desc = step_description.lower()
        
        # Fast Heuristic / Keyword-based selection 
        if "search" in desc or "look up" in desc or "find online" in desc or "web" in desc:
            return "web_search"
        elif "screen" in desc or "look at" in desc or "screenshot" in desc or "vision" in desc:
            return "vision"
        elif "telegram" in desc or "message admin" in desc or "notify" in desc or "send to" in desc:
            return "telegram_notify"
        elif "status" in desc or "memory" in desc or "cpu" in desc:
            return "system_status"
        elif "command" in desc or "shell" in desc or "terminal" in desc or "script" in desc:
            return "terminal"
        elif "mouse" in desc or "click" in desc or "keyboard" in desc or "type" in desc or "scroll" in desc or "hotkey" in desc or "press" in desc:
            return "computer_control"
        else:
            return "local_llm"

