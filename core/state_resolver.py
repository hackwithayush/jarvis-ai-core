"""
State Resolver with Hysteresis
Resolves multi-dimensional cognitive states into visual frames with hysteresis stabilization.
"""
import collections
import logging

logger = logging.getLogger("jarvis.resolver")

class StateResolver:
    def __init__(self, history_length: int = 4, stable_threshold: int = 3):
        self.history_length = history_length
        self.stable_threshold = stable_threshold
        self.history = collections.deque(maxlen=self.history_length)
        self.current_state = "idle"
        
    def resolve(self, graph_summary: dict) -> str:
        """Determines the visual state using weighted priority and applies hysteresis."""
        metrics = graph_summary.get("metrics", {})
        
        # 1. Weighted priority mathematical arbitration
        score_sleep = metrics.get("fatigue", 0.0) * 1.3
        score_combat = metrics.get("stress", 0.0) * 1.5
        score_curious = (metrics.get("curiosity", 0.0) * 1.1) + (metrics.get("focus", 0.0) * 0.4)
        score_idle = 0.40 # Baseline
        
        scores = {
            "sleep": score_sleep,
            "combat": score_combat,
            "curious": score_curious,
            "idle": score_idle
        }
        
        raw_state = max(scores, key=scores.get)
            
        # 2. Append to history buffer
        self.history.append(raw_state)
        
        # 3. Analyze history to prevent flickering (Hysteresis)
        # Count occurrences in history
        counts = collections.Counter(self.history)
        most_common_state, count = counts.most_common(1)[0]
        
        # Only transition visual state if the new state remains stable for consecutive frames
        if most_common_state != self.current_state and count >= self.stable_threshold:
            logger.info(f"[RESOLVER] State stabilized: {self.current_state} -> {most_common_state}")
            self.current_state = most_common_state
            
        return self.current_state

# Global Resolver Instance
state_resolver = StateResolver()
