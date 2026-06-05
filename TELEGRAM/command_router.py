"""
Command Router
Routes Telegram text and commands to JARVIS Brain or Remote Tasks.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from CORE.jarvis_brain import JarvisBrain
from TELEGRAM.remote_tasks import RemoteTasks
from VISION.desktop_vision import DesktopVision
from TOOLS.web_search import WebSearch

class CommandRouter:
    def __init__(self):
        self.brain = JarvisBrain()
        
    def process(self, command: str, message_text: str = "") -> dict:
        """ Routes commands. Returns dict with 'type' (text/photo) and 'content'. """
        
        if command == "/status":
            return {"type": "text", "content": RemoteTasks.get_system_status()}
            
        elif command == "/screenshot":
            path = RemoteTasks.take_screenshot()
            return {"type": "photo", "content": path}
            
        elif command == "/memory":
            return {"type": "text", "content": "Memory modules are online and functioning normally."}
            
        elif command == "/vision":
            b64_image = DesktopVision.capture_screen_base64()
            prompt = message_text.replace("/vision", "").strip()
            if not prompt:
                prompt = "Describe exactly what is on my screen."
                
            response = self.brain.process_request(prompt, has_image=True, image_base64=b64_image)
            return {"type": "text", "content": response}
            
        elif command == "/search":
            query = message_text.replace("/search", "").strip()
            if not query:
                return {"type": "text", "content": "Please provide a query: /search <topic>"}
            
            raw_results = WebSearch.search(query)
            prompt = f"Summarize these search results for the user query '{query}':\n{raw_results}"
            response = self.brain.process_request(prompt, force_heavy=True)
            return {"type": "text", "content": response}
            
        else:
            # Route general conversation to the JARVIS Brain
            response = self.brain.process_request(message_text)
            return {"type": "text", "content": response}
