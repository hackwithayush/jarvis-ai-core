"""
Execution Manager
Runs the selected tool for a step securely. Enforces safety layers (no rogue shell commands).
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from TOOLS.web_search import WebSearch
from VISION.desktop_vision import DesktopVision
from TELEGRAM.notifications import NotificationManager
from TELEGRAM.remote_tasks import RemoteTasks
from AUTONOMOUS_CORE.retry_handler import with_retry

class ExecutionManager:
    def __init__(self, brain_instance):
        self.brain = brain_instance
        self.notifier = NotificationManager()
        
    @with_retry(max_retries=2, delay=2)
    def execute_step(self, step: str, tool: str, context: str) -> str:
        print(f"\n[EXECUTION] Running step: '{step}' via Tool: [{tool.upper()}]")
        
        if tool == "web_search":
            results = WebSearch.search(step)
            return f"Web Search Results:\n{results}"
            
        elif tool == "vision":
            b64_img = DesktopVision.capture_screen_base64()
            return self.brain.process_request(f"Analyze this screen context: {step}", has_image=True, image_base64=b64_img)
            
        elif tool == "telegram_notify":
            # Extract what to send based on context
            prompt = f"Given this context:\n{context}\n\nFormat a short, clean telegram message updating the admin on the progress."
            msg = self.brain.process_request(prompt)
            self.notifier.send_alert(msg)
            return "Notification sent successfully."
            
        elif tool == "system_status":
            return RemoteTasks.get_system_status()
            
        elif tool == "terminal":
            print("[SANDBOX SHELL LAYER] Running raw command inside secure subprocess sandbox.")
            from SAFE_EXECUTION.sandbox import SafeSandbox
            sandbox = SafeSandbox()
            return sandbox.execute_command(step)
            
        elif tool == "computer_control":
            print("[AUTOMATION GRID] Performing programmatic PC automation via PyAutoGUI sandbox...")
            from SAFE_EXECUTION.sandbox import SafeSandbox
            sandbox = SafeSandbox()
            
            # Formulate the payload converting step description to python API line
            prompt = f"""
            Translate this system command into python script lines utilizing a globally imported instance named `computer_control`.
            
            Available API methods:
            - computer_control.click(x, y, clicks=1, button='left')
            - computer_control.type_text(text, press_enter=False)
            - computer_control.press_hotkey(['key1', 'key2'])
            - computer_control.scroll(amount)
            - computer_control.move_to(x, y)
            
            Command: "{step}"
            Return ONLY the valid python code block.
            """
            script = self.brain.process_request(prompt, force_heavy=True)
            clean_script = script.replace("```python", "").replace("```", "").strip()
            
            payload = f"""
from core.computer_control import computer_control
{clean_script}
"""
            return sandbox.execute_python(payload)
            
        else: # local_llm (Processing, summarizing, reasoning)
            prompt = f"Context of previous steps:\n{context}\n\nNow execute this current step: {step}"
            return self.brain.process_request(prompt)

