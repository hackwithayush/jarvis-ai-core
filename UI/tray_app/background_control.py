"""
System Tray App
Runs completely silently in the background, offering quick controls over the OS UI.
"""
import pystray
from PIL import Image, ImageDraw
import sys

def create_image(color1, color2):
    """ Generates a JARVIS Glowing Orb mock icon for the Windows taskbar tray. """
    image = Image.new('RGB', (64, 64), color1)
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=color2)
    return image

def on_open_dashboard(icon, item):
    print("[TRAY] Launching JARVIS Electron UI Dashboard...")
    # In production, this spawns the Electron React subprocess
    pass

def on_safe_mode(icon, item):
    print("[TRAY] Toggling Safe Mode. Autonomous features temporarily disabled.")
    
def on_quit(icon, item):
    print("[TRAY] Shutting down JARVIS...")
    icon.stop()
    sys.exit(0)

def run_tray():
    print("[TRAY] Mounting JARVIS to Windows Background System Tray...")
    # Futuristic deep blue glow
    icon_image = create_image('black', '#00bfff') 
    
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", on_open_dashboard),
        pystray.MenuItem("Enable Safe Mode", on_safe_mode),
        pystray.MenuItem("Quit JARVIS", on_quit)
    )
    
    icon = pystray.Icon("JARVIS", icon_image, "JARVIS AI OS", menu)
    icon.run()

if __name__ == "__main__":
    run_tray()
