"""
Active Task Queue & State Manager
Tracks the current state of JARVIS and manages the execution queue.
"""
from enum import Enum

class TaskState(Enum):
    BOOTING = "BOOTING"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SPEAKING = "SPEAKING"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    SHUTDOWN = "SHUTDOWN"

class ActiveTaskQueue:
    def __init__(self):
        self.state = TaskState.IDLE
        self.interrupt_flag = False
        
    def set_state(self, new_state: TaskState):
        """ Updates the global state of the AI OS and syncs with the UI. """
        print(f"\n[SYSTEM STATE] >>> {new_state.value}")
        self.state = new_state
        
        # Push to UI WebSocket Backend
        try:
            import requests
            requests.post("http://127.0.0.1:8000/api/set_state", json={"state": new_state.value}, timeout=1)
        except Exception:
            pass
            
    def trigger_interrupt(self):
        """ Flags the current operation for immediate termination. """
        print("\n[INTERRUPT] Cancellation signal received! Aborting current execution.")
        self.interrupt_flag = True
        self.set_state(TaskState.IDLE)
        
    def clear_interrupt(self):
        self.interrupt_flag = False
