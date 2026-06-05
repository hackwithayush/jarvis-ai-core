"""
Display Interpolation Engine
Separates True Cognitive State from Display State to provide cinematic, buttery-smooth telemetry rendering.
"""

class DisplayState:
    def __init__(self):
        self.metrics = {
            "confidence": 0.5,
            "stress": 0.0,
            "fatigue": 0.0,
            "focus": 0.5,
            "curiosity": 0.5,
            "urgency": 0.0
        }
        
    def interpolate(self, target_metrics: dict, factor: float = 0.08):
        """
        Smoothly interpolates the current display metrics toward the target true metrics.
        Called 15 times a second in the render loop.
        """
        for key in self.metrics:
            if key in target_metrics:
                target = target_metrics[key]
                current = self.metrics[key]
                # display += (real - display) * 0.08
                self.metrics[key] = current + (target - current) * factor

# Global display state instance
display_state = DisplayState()
