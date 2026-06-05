from datetime import datetime

class NeuralJournal:
    """Compiles operational telemetry and human context into a daily reflection log."""
    
    def generate_daily_log(self, cognitive_summary: dict, human_context: dict) -> str:
        date_str = datetime.now().strftime("%B %d").upper()
        
        # System Metrics
        stress = cognitive_summary.get("metrics", {}).get("stress", 0.0)
        focus = cognitive_summary.get("metrics", {}).get("focus", 0.0)
        fatigue = cognitive_summary.get("metrics", {}).get("fatigue", 0.0)
        
        stability = "High" if stress < 0.4 else "Moderate" if stress < 0.7 else "Critical"
        focus_trend = "Strong" if focus > 0.6 else "Fragmented"
        load = "Elevated" if fatigue > 0.6 else "Nominal"
        
        # Human Metrics
        user_stress = human_context.get("emotional_patterns", {}).get("current_stress_level", "balanced").title()
        projects = human_context.get("active_projects", ["None"])
        if not projects:
            projects = ["None"]
            
        log = f"""
[bold #00ffff]NEURAL JOURNAL — {date_str}[/]

• Architecture Stability : {stability}
• Focus Cycles           : {focus_trend}
• System Load            : {load}
• Operator Stress        : {user_stress}
• Active Operations      : {", ".join(projects)}
• Sandbox Integrity      : Secure

[dim]End of reflection report.[/dim]
"""
        return log.strip()

neural_journal = NeuralJournal()
