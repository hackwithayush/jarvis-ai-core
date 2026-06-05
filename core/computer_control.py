"""
Jarvis OS — Computer Control Agent
Provides safe, programmatic hardware interaction: mouse control, typing, and window hotkeys.
"""
import time
import logging
from typing import Tuple, List

logger = logging.getLogger("jarvis.computer_control")

try:
    import pyautogui
    pyautogui.FAILSAFE = True # Slam mouse to top-left to abort immediately!
    pyautogui.PAUSE = 0.5     # Dynamic delay between actions to avoid OS stuttering
except ImportError:
    pyautogui = None
    logger.warning("[COMPUTER CONTROL] PyAutoGUI is not installed! Simulating all OS actions.")

class ComputerControlAgent:
    def __init__(self):
        self.active = pyautogui is not None
        print("[COMPUTER CONTROL] Automation Node active. Failsafe enabled: move cursor to top-left corner to abort.")
        
    def get_screen_size(self) -> Tuple[int, int]:
        """ Gathers current desktop boundaries. """
        if self.active:
            return pyautogui.size()
        return (1920, 1080)
        
    def move_to(self, x: int, y: int, duration: float = 0.5) -> bool:
        """ Smoothly slides mouse cursor to screen coordinates. """
        if not self.active:
            print(f"[SIMULATED MOUSE] Moving smoothly to ({x}, {y}) in {duration}s")
            return True
            
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            logger.error(f"Mouse Movement failed: {e}")
            return False
            
    def click(self, x: int = None, y: int = None, clicks: int = 1, button: str = 'left') -> bool:
        """ Programmatic mouse clicking (left/right/double/triple). """
        if not self.active:
            print(f"[SIMULATED MOUSE] Clicking {button} button at ({x}, {y}) {clicks} time(s).")
            return True
            
        try:
            if x is not None and y is not None:
                pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            else:
                pyautogui.click(clicks=clicks, button=button)
            return True
        except Exception as e:
            logger.error(f"Mouse Click failed: {e}")
            return False
            
    def drag_to(self, x: int, y: int, duration: float = 1.0, button: str = 'left') -> bool:
        """ Programmatic mouse dragging. """
        if not self.active:
            print(f"[SIMULATED MOUSE] Dragging {button} to ({x}, {y}) in {duration}s")
            return True
            
        try:
            pyautogui.dragTo(x, y, duration=duration, button=button)
            return True
        except Exception as e:
            logger.error(f"Mouse Drag failed: {e}")
            return False
            
    def type_text(self, text: str, press_enter: bool = False) -> bool:
        """ Programmatically type a text string. """
        if not self.active:
            print(f"[SIMULATED KEYBOARD] Typing: '{text}' (Enter={press_enter})")
            return True
            
        try:
            pyautogui.write(text, interval=0.05)
            if press_enter:
                pyautogui.press('enter')
            return True
        except Exception as e:
            logger.error(f"Keyboard input failed: {e}")
            return False
            
    def press_hotkey(self, keys: List[str]) -> bool:
        """ Programmatically trigger complex shortcut keys (e.g. ['alt', 'tab'] or ['win', 'd']). """
        if not self.active:
            print(f"[SIMULATED KEYBOARD] Pressing hotkeys: {keys}")
            return True
            
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"Hotkey sequence failed: {e}")
            return False
            
    def scroll(self, amount: int) -> bool:
        """ Programmatic scroll of the active window context. """
        if not self.active:
            print(f"[SIMULATED MOUSE] Scrolling: {amount}")
            return True
            
        try:
            pyautogui.scroll(amount)
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False

# Global Instance
computer_control = ComputerControlAgent()
