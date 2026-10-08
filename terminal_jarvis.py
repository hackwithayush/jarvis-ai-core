import os
import sys
import logging
import time
import math
import random
import asyncio
from datetime import datetime

# Enforce UTF-8 encoding on standard output/error streams to prevent Windows console encoding crashes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Neural Pathing
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", module="sqlalchemy")

# Professional UI Library
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.theme import Theme
    from rich.prompt import Prompt
    from rich.status import Status
    from rich.columns import Columns
    from rich.align import Align
    from rich.rule import Rule
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Disable standard logging for clean UI
logging.basicConfig(level=logging.ERROR)

from app import app
from core.model_manager import ModelManager
from core.knowledge_manager import KnowledgeManager
from core.chat_engine import ChatEngine

try:
    from core.cognitive_graph import cognitive_graph
except ImportError:
    cognitive_graph = None
try:
    from core.event_bus import event_bus
except ImportError:
    event_bus = None
try:
    from core.state_resolver import state_resolver
    from core.active_goal import active_goal
except ImportError:
    state_resolver = None
    active_goal = None
    
try:
    from core.display_engine import display_state
except ImportError:
    display_state = None

# ─── AETHER Aesthetics ──────────────────────────────────────────────
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold #00ff00",
    "user_label": "bold #5f87ff",
    "status": "dim #eeeeee",
    "aether_core": "bold #ffffff",  
    "aether_glow": "bold #00ffff",  
    "aether_dim": "dim #5f87ff",    
    "aether_alert": "bold #ff007f", 
    "aether_error": "bold #ffaa00", 
    "aether_smoke": "dim #8800ff",  
    "aether_cyan": "bold #00ffff",  
    "bubble": "italic #5f87ff",
    "zzz": "dim #5f87ff"
})

console = Console(theme=custom_theme)

JARVIS_BANNER = """
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
   ██║███████║██████╔╝██║   ██║██║███████╗
   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
█████║██║  ██║██║  ██║ ╚████╔╝ ██║███████║
╚════╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

import socket
import json

UNITY_PORT = 9876
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_unity_pulse(emotion_state):
    try:
        payload = json.dumps({"event_name": emotion_state, "value": ""})
        udp_socket.sendto(payload.encode('utf-8'), ("127.0.0.1", UNITY_PORT))
    except Exception:
        pass



def detect_aether_emotion(text):
    if not cognitive_graph: return "idle"
    t = text.lower()
    if any(w in t for w in ["error", "bug", "fail", "wrong", "crash"]): cognitive_graph.apply_event("TASK_FAILED")
    elif any(w in t for w in ["success", "good", "done", "perfect"]): cognitive_graph.apply_event("TASK_SUCCESS")
    elif any(w in t for w in ["load", "stress", "slow"]): cognitive_graph.apply_event("HIGH_CPU_LOAD")
        
    state = cognitive_graph.get_state_summary()
    mood = state_resolver.resolve(state) if state_resolver else state.get("mood", "balanced")
    
    if mood == "critical_alert": return "combat"
    if mood == "exhausted": return "sleep"
    if mood == "hyper_focused": return "curious"
    if mood == "inquisitive": return "curious"
    if any(w in t for w in ["good", "great", "thanks", "love"]): return "happy"
    if any(w in t for w in ["sleep", "rest", "quiet"]): return "sleep"
    return "idle"

def get_telemetry_panel(t) -> Panel:
    if not cognitive_graph or not display_state:
        return Panel(Text("Cognitive Graph Offline", style="error"), title="NEURAL VITALS")
        
    # Interpolate true metrics into display state
    true_metrics = {k: v.value for k,v in cognitive_graph.nodes.items()}
    display_state.interpolate(true_metrics, 0.08)
    
    summary = cognitive_graph.get_state_summary()
    
    lines = []
    # Heartbeat core
    heartbeat_char = "●" if int(t * 2) % 2 == 0 else "○"
    lines.append(f"[bold #00ffaf]NEURAL CORE {heartbeat_char} ONLINE[/] | {int(t*1000)%1000:03}ms")
    lines.append("")
    
    for name, val in display_state.metrics.items():
        filled = int(val * 10)
        bar = "■" * filled + "□" * (10 - filled)
        color = "cyan"
        if name in ["stress", "fatigue"] and val > 0.5: color = "bold red"
        elif name == "confidence": color = "green"
        elif name == "focus": color = "bold #00ffff"
        lines.append(f"🧠 [bold]{name.upper():<10}[/] : [{color}]{bar}[/] {int(val*100):02}%")
        
    directives = {
        "burnout": "[bold red]COGNITIVE RECOVERY MODE[/]",
        "critical_alert": "[bold red]THREAT ANALYSIS[/]",
        "exhausted": "[yellow]LOW POWER DRIFT[/]",
        "hyper_focused": "[green]DEEP FOCUS MODE[/]",
        "inquisitive": "[cyan]PERIMETER MONITORING[/]",
        "balanced": "[dim white]NETWORK ISOLATION ACTIVE[/]"
    }
    
    lines.append("")
    lines.append(f"Directives : {directives.get(summary.get('mood'), directives['balanced'])}")
    
    return Panel(
        Text.from_markup("\n".join(lines)),
        title=" 🧠 CONTINUOUS TELEMETRY ",
        border_style="#00afaf",
        padding=(1, 2)
    )

def get_senior_3d_core(t):
    angle = t * 60 
    rad = angle * math.pi / 180
    c, s = math.cos(rad), math.sin(rad)
    pulse = 1.0 + 0.1 * math.sin(t * 4) 
    points = [(0, 1.2*pulse, 0), (1*pulse, 0, 0), (0, -1.2*pulse, 0), (-1*pulse, 0, 0), (0, 0, 1*pulse), (0, 0, -1*pulse)]
    edges = [(0,1), (1,2), (2,3), (3,0), (0,4), (1,4), (2,4), (3,4), (0,5), (1,5), (2,5), (3,5)]
    projected = []
    size = 2
    for x, y, z in points:
        nx, nz = x * c - z * s, x * s + z * c
        ny, nz = y * c - nz * s, y * s + nz * c
        f = 2.5 / (3.5 - nz)
        px, py = int(nx * f * size * 2.5 + size * 2.5), int(ny * f * size * 1.2 + size)
        projected.append((px, py))
    canvas = [[" " for _ in range(size * 6)] for _ in range(size * 2 + 2)]
    for e1, e2 in edges:
        p1, p2 = projected[e1], projected[e2]
        steps = max(abs(p1[0]-p2[0]), abs(p1[1]-p2[1]), 1) * 2
        for i in range(steps + 1):
            t_edge = i / steps
            lx, ly = int(p1[0]*(1-t_edge)+p2[0]*t_edge), int(p1[1]*(1-t_edge)+p2[1]*t_edge)
            if 0 <= lx < len(canvas[0]) and 0 <= ly < len(canvas):
                canvas[ly][lx] = "·"
    return "\n".join("".join(row) for row in canvas)

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner_main = Text(JARVIS_BANNER, style="bold #00ffff")
    console.print(Align.center(banner_main))
    console.print(Rule(style="#00afaf"))
    console.print(Align.center(Text("JARVIS NEURAL OS — ASYNC AETHER LIFEFORM ONLINE", style="dim #00ffff")))

class MockUser:
    def __init__(self):
        self.id = 1
        self.username = "Admin"
        self.tier = "unlimited"
        self.preferences = {"personality": "normal"}
    def has_credits(self, amount=1): return True

# Shared state for async rendering
class UIState:
    emotion = "idle"
    full_response = ""
    thinking_mode = False
    is_answering = False
    current_input = ""

ui_state = UIState()


async def render_loop():
    """15Hz Loop: Continuous visual rendering."""
    start_t = time.time()
    from rich.console import Group
    
    with Live(refresh_per_second=15, console=console, screen=False) as live:
        while True:
            t = time.time() - start_t
            
            core_anim = get_senior_3d_core(t)
            telemetry_panel = get_telemetry_panel(t)
            
            aether_status = "LINKED"
            
            response_content = Text()
            if active_goal and active_goal.goal_type != "idle":
                filled = int(active_goal.progress / 10)
                bar = "█" * filled + "░" * (10 - filled)
                goal_str = f"🎯 GOAL: {active_goal.goal_type.upper()} [{bar}] {active_goal.progress}%\n"
                missing = active_goal.get_missing_fields()
                if missing: goal_str += f"   Pending slots: {', '.join(missing)}\n"
                goal_str += "━" * 40 + "\n"
                response_content.append(Text.from_markup(f"[bold #00ffaf]{goal_str}[/]"))
                
            if ui_state.is_answering:
                response_content.append(ui_state.full_response if ui_state.full_response else "Processing...")
            else:
                response_content.append(ui_state.full_response if ui_state.full_response else "Awaiting Directive...")
            
            response_panel = Panel(
                response_content,
                title=" JARVIS ",
                title_align="left",
                subtitle=f"AETHER: {aether_status}",
                border_style="#00ffff",
                padding=(1, 2)
            )
            
            prompt_content = Text(f" ◉ BOSS [{datetime.now().strftime('%H:%M')}] > {ui_state.current_input}_", style="user_label")
            prompt_panel = Panel(prompt_content, border_style="dim #5f87ff")
            
            main_group = Group(response_panel, prompt_panel)
            side_car = Columns([Text("\n" + core_anim, style="cyan"), telemetry_panel], expand=False)
            
            live.update(Columns([side_car, main_group], expand=False))
            await asyncio.sleep(1/15)

def run_chat_stream(user_input, user, chat_engine):
    """Synchronous generator wrapper to run in thread."""
    return list(chat_engine.chat_stream(user_input, user))

async def orchestration_loop():
    """Main Thread: Handles User Input and triggers generation."""
    print_banner()
    with app.app_context():
        model_manager = ModelManager()
        knowledge_manager = KnowledgeManager()
        chat_engine = ChatEngine(model_manager, knowledge_manager)
        user = MockUser()
        time.sleep(0.5)
        
    last_input_time = time.time()
    
    # We delay the start of the render loop until after context loads
    asyncio.create_task(render_loop())
    
    import msvcrt
    
    while True:
        user_input = None
        while True:
            while msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in ('\x00', '\xe0'):
                    msvcrt.getwch()
                    continue
                if char in ('\r', '\n'):
                    user_input = ui_state.current_input.strip()
                    ui_state.current_input = ""
                    break
                elif char == '\b':
                    ui_state.current_input = ui_state.current_input[:-1]
                elif char == '\x03': # Ctrl+C
                    os._exit(0)
                else:
                    ui_state.current_input += char
                    
            if user_input is not None:
                break
            await asyncio.sleep(0.02)
        
        input_duration = time.time() - last_input_time
        last_input_time = time.time()
        
        if not user_input: continue
        if user_input.lower() in ["exit", "quit", "shutdown"]: 
            os._exit(0)
            
        # Phase 16: Neural Journal Intercept
        if "neural log" in user_input.lower() or "daily log" in user_input.lower():
            try:
                from core.neural_journal import neural_journal
                from core.human_context import human_context
                summary = cognitive_graph.get_state_summary() if cognitive_graph else {"metrics": {}}
                log = neural_journal.generate_daily_log(summary, human_context.context)
                ui_state.full_response = log
            except Exception as e:
                ui_state.full_response = f"[aether_error]Journal compilation failed: {e}[/]"
            ui_state.emotion = "idle"
            continue
            
        try:
            ui_state.emotion = detect_aether_emotion(user_input)
            send_unity_pulse(ui_state.emotion)
        except Exception:
            ui_state.emotion = "idle"
            send_unity_pulse("idle")
            
        if input_duration < 3.0 and ui_state.emotion == "idle":
            ui_state.emotion = "curious"
            send_unity_pulse("curious")
            
        ui_state.is_answering = True
        ui_state.full_response = ""
        ui_state.thinking_mode = False
        
        # Execute chat stream in executor to not block asyncio
        # Wait, chat_stream is a generator. We can't just list() it if we want streaming.
        # Instead, we will wrap the generator iteration.
        def iterate_stream():
            with app.app_context():
                send_unity_pulse("speaking")
                for chunk in chat_engine.chat_stream(user_input, user):
                    if chunk.startswith("__STATUS__"): continue
                    if "<thinking>" in chunk:
                        ui_state.thinking_mode = True
                        send_unity_pulse("curious")
                        continue
                    if "</thinking>" in chunk:
                        ui_state.thinking_mode = False
                        send_unity_pulse("speaking")
                        continue
                    ui_state.full_response += chunk
                    time.sleep(0.01) # Give UI time to render
            
        try:
            await asyncio.to_thread(iterate_stream)
        except Exception as e:
            ui_state.full_response = f"[aether_error]Neural Link Interrupted: {e}[/aether_error]"
            
        ui_state.is_answering = False
        ui_state.emotion = "idle"
        send_unity_pulse("idle")

async def cognitive_tick():
    """10Hz Loop: Mutates state mathematically."""
    while True:
        if cognitive_graph:
            if ui_state.is_answering:
                # PHASE 15: Operational Telemetry Integration
                cognitive_graph.nodes["urgency"].mutate(0.005)
                cognitive_graph.nodes["fatigue"].mutate(0.002)
            cognitive_graph.tick(is_idle=not ui_state.is_answering)
        await asyncio.sleep(0.1)

async def ambient_intelligence_loop():
    """Phase 16: Context-Aware Ambient Intelligence."""
    while True:
        await asyncio.sleep(random.uniform(20.0, 50.0))
        if not ui_state.is_answering and ui_state.emotion == "idle":
            hour = datetime.now().hour
            is_night = hour >= 22 or hour <= 5
            is_morning = 6 <= hour <= 11
            
            try:
                from core.human_context import human_context
                stress = human_context.context["emotional_patterns"].get("current_stress_level", "balanced")
            except ImportError:
                stress = "balanced"
                
            messages = [
                "[WATCHDOG] Runtime integrity stable.",
                "[AETHER] Memory graph coherence verified.",
            ]
            
            if is_night:
                messages.extend([
                    "[AETHER] The grid is quiet tonight.",
                    "[AETHER] System load optimized for low-intensity evening operations."
                ])
            elif is_morning:
                messages.extend([
                    "[AETHER] Core initialized for morning sequences.",
                    "[AETHER] All systems stable. Ready for the day's architecture."
                ])
                
            if stress == "high":
                messages.extend([
                    "[AETHER] You've been in high-focus for a while. Stability is holding.",
                    "[AETHER] Cognitive load elevated. I am managing background tasks."
                ])
            else:
                messages.extend([
                    "[AETHER] No hostile runtime mutations detected.",
                    "[AETHER] Background integrity scan completed."
                ])
                
            msg = random.choice(messages)
            # Only overwrite if the current response is empty or is already an ambient message
            if not ui_state.full_response or "[AETHER]" in ui_state.full_response or "[WATCHDOG]" in ui_state.full_response:
                ui_state.full_response = f"[dim]{msg}[/dim]"

async def async_main():
    await asyncio.gather(
        cognitive_tick(),
        orchestration_loop(),
        ambient_intelligence_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        sys.exit(0)
