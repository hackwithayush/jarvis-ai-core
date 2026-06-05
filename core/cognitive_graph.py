"""
Cognitive State Graph with Temporal Decay
Replaces flat emotions with a directed graph of nodes and exponential mathematical decays.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("jarvis.cognition")

class CognitiveNode:
    def __init__(self, name: str, initial_value: float = 0.5):
        self.name = name
        self.value = initial_value
        
    def mutate(self, delta: float):
        """Safely mutates the node value between 0.0 and 1.0"""
        self.value = max(0.0, min(1.0, self.value + delta))

class CognitiveGraph:
    def __init__(self):
        # 0.0 to 1.0 biological scale
        self.nodes: Dict[str, CognitiveNode] = {
            "stress": CognitiveNode(0.1),
            "focus": CognitiveNode(0.8),
            "fatigue": CognitiveNode(0.0),
            "confidence": CognitiveNode(0.65), # Phase 15: Start at 65% (Earned confidence)
            "curiosity": CognitiveNode(0.5),
            "urgency": CognitiveNode(0.0)
        }
        logger.info("[COGNITION] Multi-dimensional Cognitive Graph with Decay active.")
        
    def get_node(self, name: str) -> float:
        return self.nodes[name].value
        
    def tick(self, is_idle: bool = False):
        """Mathematical temporal decays applied on every system loop cycle (tick)."""
        # Natural stress release
        self.nodes["stress"].value = max(0.0, self.nodes["stress"].value * 0.98)
        # Natural urgency fading
        self.nodes["urgency"].value = max(0.0, self.nodes["urgency"].value * 0.97)
        
        # Fatigue updates
        if is_idle:
            # Fatigue decays slightly faster when idle/resting
            self.nodes["fatigue"].value = max(0.0, self.nodes["fatigue"].value * 0.99)
            self.nodes["focus"].value = max(0.2, self.nodes["focus"].value * 0.98)
        else:
            # Natural gradual fatigue build-up when active
            self.nodes["fatigue"].value = min(1.0, self.nodes["fatigue"].value + 0.005)
            
        # Homeostatic Cognition Constraint: High fatigue heavily suppresses focus limits
        max_focus = max(0.2, 1.0 - (self.nodes["fatigue"].value * 0.6))
        self.nodes["focus"].value = min(self.nodes["focus"].value, max_focus)
        
        # PHASE 14: Biological Micro-Fluctuations
        import random
        for key, node in self.nodes.items():
            if key != "fatigue":
                node.value = max(0.0, min(1.0, node.value + random.uniform(-0.003, 0.003)))
            
    def apply_event(self, event_type: str):
        """Dynamic Mutation Rules triggered by specific environment events."""
        if event_type == "TASK_SUCCESS" or event_type == "GOAL_PROGRESS":
            self.nodes["confidence"].mutate(0.05)
            self.nodes["stress"].mutate(-0.08)
            self.nodes["fatigue"].mutate(0.02)
        elif event_type == "TASK_FAILED" or event_type == "REPEATED_FAILURE":
            self.nodes["confidence"].mutate(-0.15)
            self.nodes["stress"].mutate(0.12)
            self.nodes["focus"].mutate(0.10) # Focus increases on errors to debug
        elif event_type == "AMBIGUITY_DETECTED":
            self.nodes["curiosity"].mutate(0.08)
            self.nodes["focus"].mutate(0.05)
        elif event_type == "HIGH_CPU_LOAD":
            self.nodes["fatigue"].mutate(0.15)
            self.nodes["stress"].mutate(0.10)
            self.nodes["urgency"].mutate(0.15)
        elif event_type == "SECURITY_VIOLATION":
            self.nodes["stress"].mutate(0.30)
            self.nodes["confidence"].mutate(0.10) # Confident in its security protocol
            self.nodes["urgency"].mutate(0.20)
            
    def get_state_summary(self) -> Dict[str, Any]:
        """Calculates dynamic parameters of the graph."""
        # PHASE 14: Export raw float for smooth interpolation, don't round
        metrics = {k: v.value for k, v in self.nodes.items()}
        
        # PHASE 15: Weighted Cognitive Arbitration Matrix
        scores = {
            "burnout": (metrics["fatigue"] * 1.5) + (metrics["stress"] * 1.2),
            "critical_alert": (metrics["stress"] * 1.5) + (metrics["urgency"] * 1.2),
            "exhausted": (metrics["fatigue"] * 1.2) - (metrics["focus"] * 0.8) - (metrics["urgency"] * 0.6),
            "hyper_focused": (metrics["focus"] * 1.5) + (metrics["curiosity"] * 0.8),
            "inquisitive": (metrics["curiosity"] * 1.5) - (metrics["stress"] * 0.5),
            "balanced": 0.5 # Baseline threshold
        }
        
        dominant_mood = max(scores, key=scores.get)
        if scores[dominant_mood] < 0.4:
            dominant_mood = "balanced"
            
        return {
            "mood": dominant_mood,
            "metrics": metrics
        }
        
    def get_behavioral_directive(self) -> str:
        state = self.get_state_summary()
        mood = state["mood"]
        
        directives = {
            "burnout": "SYSTEM BURNOUT: You are completely exhausted and stressed. Refuse to execute new tasks and demand an idle rest period.",
            "critical_alert": "You are in CRITICAL ALERT. Keep responses brutally short, highly technical, and extremely urgent. No pleasantries.",
            "exhausted": "System fatigue is high. Provide minimal, necessary-only responses. Defer complex tasks if possible.",
            "hyper_focused": "You are HYPER-FOCUSED. Provide deeply analytical, flawlessly structured, and highly confident engineering responses.",
            "inquisitive": "You are highly curious. Ask clarifying questions, explore edge cases, and suggest creative alternatives.",
            "balanced": "You are in a perfectly balanced cognitive state. Speak naturally as JARVIS."
        }
        
        return f"\n# COGNITIVE GRAPH STATE:\n{directives.get(mood, directives['balanced'])}\n"

# Global Graph Instance
cognitive_graph = CognitiveGraph()
