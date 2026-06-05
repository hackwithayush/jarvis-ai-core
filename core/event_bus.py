"""
Neural Task Bus
Centralized thread-safe Event Bus for JARVIS Operating System.
Replaces direct agent-to-agent calls with async Pub/Sub messaging.
"""
import threading
import queue
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("jarvis.event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue = queue.Queue()
        self._running = False
        self._worker_thread = None
        self._lock = threading.Lock()
        
    def start(self):
        """Starts the background event processing loop."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_events, daemon=True, name="NeuralEventBus")
        self._worker_thread.start()
        logger.info("[EVENT BUS] Neural Task Bus initialized and running.")
        
    def stop(self):
        """Stops the event processing loop gracefully."""
        self._running = False
        if self._worker_thread:
            # Inject a dummy event to break out of blocking queue get
            self._event_queue.put(("_SHUTDOWN", None))
            self._worker_thread.join(timeout=2.0)
            logger.info("[EVENT BUS] Neural Task Bus shut down.")
            
    def subscribe(self, topic: str, callback: Callable[[Any], None]):
        """Register a callback function to a specific event topic."""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)
                
    def unsubscribe(self, topic: str, callback: Callable[[Any], None]):
        """Remove a registered callback from a topic."""
        with self._lock:
            if topic in self._subscribers and callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)
                
    def publish(self, topic: str, payload: Any = None):
        """Push an event to the queue to be broadcasted to all subscribers asynchronously."""
        self._event_queue.put((topic, payload))
        logger.debug(f"[EVENT BUS] Event published: {topic}")
        
    def _process_events(self):
        """Background loop dispatching events to registered subscribers."""
        while self._running:
            try:
                topic, payload = self._event_queue.get(timeout=1.0)
                if topic == "_SHUTDOWN":
                    break
                    
                with self._lock:
                    # Get copy of callbacks to avoid locking during execution
                    callbacks = self._subscribers.get(topic, []).copy()
                    
                for callback in callbacks:
                    try:
                        callback(payload)
                    except Exception as e:
                        logger.error(f"[EVENT BUS ERROR] Subscriber {callback.__name__} failed on topic '{topic}': {e}")
                        
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[EVENT BUS FATAL] Worker thread error: {e}")

# Global instance
event_bus = EventBus()
# Auto-start on import
event_bus.start()
