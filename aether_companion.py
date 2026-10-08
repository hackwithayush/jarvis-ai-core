"""
AETHER ASCII Companion — Standalone Terminal Visualizer
Connects with JARVIS via UDP port 9876 to mirror states and render in real-time.
"""
import socket
import json
import time
import math
import random
import threading
import sys
import os
from datetime import datetime

from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.layout import Layout

# UDP Listener Configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 9876

console = Console()

class AetherCompanion:
    def __init__(self):
        self.x = 0
        self.direction = 1
        self.state = "idle" 
        self.last_update = time.time()
        self.idle_since = time.time()
        self.bubble_text = ""
        self.bubble_expiry = 0
        self.energy = 100.0
        self.bond_level = 0.0
        self.head_turn = 0 
        self.last_head_turn = time.time()
        self.paw_state = 0
        self.recent_events = []
        
    def add_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_events.append(f"[{timestamp}] {msg}")
        if len(self.recent_events) > 8:
            self.recent_events.pop(0)

    def update(self, emotion="idle"):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        hour = datetime.now().hour
        is_night = hour >= 23 or hour <= 5
        
        if emotion != "idle":
            self.state = emotion
            self.idle_since = now
            self.energy = max(0.0, self.energy - 0.5)
            self.bond_level = min(100.0, self.bond_level + 0.5)
        else:
            idle_time = now - self.idle_since
            new_state = self.state
            if is_night and idle_time > 15: 
                new_state = "sleep"
            elif is_night and emotion == "idle": 
                new_state = "concerned"
            elif idle_time > 45: 
                new_state = "sleep"
                self.energy = min(100.0, self.energy + dt * 2)
            elif idle_time > 20: 
                new_state = "lonely"
            elif self.state not in ["idle", "walking", "concerned", "lonely"]:
                if random.random() < 0.05: 
                    new_state = "idle"
                
            self.state = new_state
            
            if self.state in ["idle", "walking"]:
                if random.random() < 0.005: 
                    self.state = "walking" if self.state == "idle" else "idle"
                if random.random() < 0.02: 
                    self.direction *= -1
                    
            if random.random() < 0.003 and now > self.bubble_expiry:
                quotes = [
                    "Systems nominal.", 
                    "Monitoring...", 
                    f"Bond: {int(self.bond_level)}%", 
                    "Quiet night." if is_night else "Ready for input."
                ]
                if self.state == "sleep": 
                    quotes = ["Zzz...", "Dreaming of the grid..."]
                self.bubble_text = random.choice(quotes)
                self.bubble_expiry = now + 4

        if self.state == "walking":
            self.x += self.direction * dt * 2.5
            if abs(self.x) > 5: 
                self.direction *= -1

        if now - self.last_head_turn > 2.0:
            if random.random() < 0.3:
                self.head_turn = random.choice([-1, 0, 1])
                self.last_head_turn = now
            elif random.random() < 0.4:
                self.paw_state = 1 - self.paw_state
                self.last_head_turn = now

    def get_frame(self, t):
        breathing = math.sin(t * 2.5) * 0.12 
        blinking = random.random() < 0.03 
        ear_twitch = random.random() < 0.05 
        flicker = random.random() < 0.01 
        
        # Theme colors
        eye_color = "bold #ffffff"
        body_color = "bold #00ffff" if not flicker else "dim #5f87ff"
        chest_color = "bold #00ffff" if math.sin(t * 4) > 0 else "bold #008888" 
        smoke_char = "░" if int(t * 4) % 2 == 0 else "▒"
        
        ears_str = " /|   |\\ "
        eyes_str = "  ◉   ◉  "
        mouth_str = "   ▼   "
        
        if self.head_turn == -1: 
            ears_str = "/|   |\\  "
            eyes_str = " ◉   ◉   "
            mouth_str = "  ▼    "
        elif self.head_turn == 1: 
            ears_str = "  /|   |\\"
            eyes_str = "   ◉   ◉ "
            mouth_str = "    ▼  "
            
        if ear_twitch: 
            ears_str = ears_str.replace("/|", "_/").replace("|\\", "\\_")
            
        if self.state == "sleep":
            ears_str = "         "
            body_top = "  ╭───╮  "
            eyes_str = "  - v -  "
            mouth_str= "  ╰───╯  "
            breathing = math.sin(t * 1.0) * 0.08
            eye_color = body_color = chest_color = "dim #5f87ff"
        elif self.state == "curious":
            ears_str = " /|   _/ "
            eyes_str = "  ◉   ◉  " if not blinking else "  -   -  "
            mouth_str = "   ~   "
            breathing = math.sin(t * 4) * 0.2
            self.head_turn = 0 
            body_top = "  █████  "
        elif self.state in ["combat", "alert"]:
            ears_str = " ⚡   ⚡ "
            eyes_str = "  >   <  "
            mouth_str = "   w   "
            eye_color = chest_color = "bold #ff007f"
            body_color = "bold white"
            smoke_char = "▓"
            body_top = "  █████  "
        elif self.state == "error":
            ears_str = " /|   |\\ "
            eyes_str = "  O   O  "
            mouth_str = "   =   "
            eye_color = chest_color = "bold #ffaa00"
            body_top = "  █████  "
        elif self.state == "lonely":
            ears_str = " \\_   _/ "
            eyes_str = "  •   •  "
            mouth_str = "   -   "
            eye_color = "dim #5f87ff"
            breathing = math.sin(t * 1.5) * 0.1
            body_top = "  █████  "
        elif self.state == "concerned":
            ears_str = " /_   _\\ "
            eyes_str = "  o   o  "
            mouth_str = "   ~   "
            eye_color = "yellow"
            body_top = "  █████  "
        elif self.state == "speaking":
            ears_str = " /|   |\\ "
            eyes_str = "  ◉   ◉  " if not blinking else "  -   -  "
            mouth_str = "   ○   " if int(t * 8) % 2 == 0 else "   ●   "
            breathing = math.sin(t * 5.0) * 0.15
            eye_color = "bold #ffffff"
            chest_color = "bold #00ffff"
            body_top = "  █████  "
        else: 
            body_top = "  █████  "

        if blinking and self.state not in ["sleep", "combat"]: 
            eyes_str = "  -   -  "

        smoke_l = f"[dim #8800ff]{smoke_char}[/dim #8800ff]"
        smoke_r = f"[dim #8800ff]{smoke_char}[/dim #8800ff]"
        paws = "░▒▓▒░" if self.paw_state == 0 else "▒░▓░▒"
        
        model = [
            f"   [{body_color}]{ears_str}[/]   ",
            f"  {smoke_l}[{body_color}]{body_top}[/]{smoke_r}  ",
            f" {smoke_l}[{body_color}]█[/][{eye_color}]{eyes_str}[/][{body_color}]█[/]{smoke_l} ",
            f"  {smoke_l}[{chest_color}]██[/][bold #ffffff]{mouth_str}[/][{chest_color}]██[/]{smoke_r}  ",
            f"   {smoke_l}[{body_color}]{paws}[/]{smoke_r}   "
        ]
        
        if self.state == "sleep": 
            model[0] += f" [dim white]{'z' * (int(t)%3 + 1)}[/]"
        elif self.state == "happy": 
            model[4] += " [bold #00ffff]~[/]" if int(t*6)%2==0 else " [bold #00ffff]>[/]"
        elif self.state == "walking": 
            model[4] += " [dim #5f87ff].[/]" if int(t*4)%2==0 else " "
            
        bubble = f"[bold cyan]⟨ {self.bubble_text} ⟩[/bold cyan]\n" if time.time() < self.bubble_expiry else "\n"
        v_pad = [""] * int(1 + breathing)
        x_pad = " " * int(6 + self.x)
        
        final_text = Text.from_markup(bubble)
        final_text.append(Text.from_markup("\n".join(v_pad + [x_pad + line for line in model])))
        return final_text

def udp_listener(companion):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
        companion.add_log(f"Socket bound. Listening on {UDP_IP}:{UDP_PORT}")
    except Exception as e:
        companion.add_log(f"CRITICAL: Port {UDP_PORT} in use: {e}")
        companion.add_log("Ensure Unity or another Aether instance is closed!")
        return

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            payload = json.loads(data.decode("utf-8"))
            event = payload.get("event_name", "idle")
            companion.add_log(f"Pulse → '{event}' received from {addr[0]}")
            companion.update(emotion=event)
        except Exception as e:
            companion.add_log(f"Listener Error: {e}")
            time.sleep(1)

def make_layout(companion, t):
    layout = Layout()
    layout.split_row(
        Layout(name="left", ratio=3),
        Layout(name="right", ratio=4)
    )
    
    companion_text = companion.get_frame(t)
    layout["left"].update(
        Panel(
            Align.center(companion_text, vertical="middle"),
            title=" AETHER ASCII CORE ",
            border_style="#00ffff"
        )
    )
    
    layout["right"].split_column(
        Layout(name="vitals", ratio=2),
        Layout(name="logs", ratio=3)
    )
    
    # Vitals Panel
    vitals_text = Text()
    vitals_text.append("Emotion State : ", style="dim")
    vitals_text.append(f"{companion.state.upper()}\n", style="bold #00ffff")
    
    energy_filled = int(companion.energy / 10)
    energy_bar = "■" * energy_filled + "□" * (10 - energy_filled)
    vitals_text.append("Energy Core   : ", style="dim")
    vitals_text.append(f"[{energy_bar}] {int(companion.energy)}%\n", style="bold green" if companion.energy > 30 else "bold red")
    
    bond_filled = int(companion.bond_level / 10)
    bond_bar = "♥" * bond_filled + "♡" * (10 - bond_filled)
    vitals_text.append("Bond Level    : ", style="dim")
    vitals_text.append(f"[{bond_bar}] {int(companion.bond_level)}%\n", style="bold #ff007f")
    
    vitals_text.append("Time Active   : ", style="dim")
    vitals_text.append(f"{datetime.now().strftime('%H:%M:%S')}\n", style="dim white")
    
    layout["right"]["vitals"].update(
        Panel(
            vitals_text,
            title=" COMPANION VITALS ",
            border_style="green"
        )
    )
    
    # Logs Panel
    logs_lines = "\n".join(companion.recent_events)
    layout["right"]["logs"].update(
        Panel(
            Text(logs_lines if logs_lines else "No pulses recorded yet."),
            title=" NEURAL PULSE TELEMETRY ",
            border_style="dim #5f87ff"
        )
    )
    
    return layout

if __name__ == "__main__":
    companion = AetherCompanion()
    
    # Start UDP listener thread
    listener_thread = threading.Thread(target=udp_listener, args=(companion,))
    listener_thread.daemon = True
    listener_thread.start()
    
    os.system('cls' if os.name == 'nt' else 'clear')
    start_t = time.time()
    
    try:
        with Live(refresh_per_second=15, screen=True) as live:
            while True:
                t = time.time() - start_t
                companion.update()
                live.update(make_layout(companion, t))
                time.sleep(1/15)
    except KeyboardInterrupt:
        sys.exit(0)
