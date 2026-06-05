"""
Remote Tasks
Handles OS-level remote commands like taking screenshots or system status.
"""
import psutil
import pyautogui
import os

class RemoteTasks:
    @staticmethod
    def get_system_status() -> str:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        return f"🖥️ **JARVIS System Status:**\n- CPU Load: {cpu}%\n- Memory (RAM): {ram}%"
        
    @staticmethod
    def take_screenshot() -> str:
        """ Takes a screenshot and returns the file path. """
        path = "screenshot.png"
        pyautogui.screenshot(path)
        return path
