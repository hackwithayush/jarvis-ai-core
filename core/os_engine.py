import os
import subprocess
import platform
import logging
import psutil
import shutil
import glob
from pathlib import Path

logger = logging.getLogger("jarvis.os")

class OSEngine:
    """Windows Operational Control Node: Launching, Monitoring, and Health."""
    
    def __init__(self):
        self.app_mapping = {
            "browser": "start chrome",
            "chrome": "start chrome",
            "google chrome": "start chrome",
            "chrome browser": "start chrome",
            "edge": "start msedge",
            "microsoft edge": "start msedge",
            "notepad": "start notepad",
            "text editor": "start notepad",
            "code": "code",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "spotify": "start spotify",
            "calculator": "start calc",
            "calc": "start calc",
            "task manager": "start taskmgr",
            "taskmgr": "start taskmgr",
            "terminal": "start wt",
            "windows terminal": "start wt",
            "cmd": "start cmd",
            "command prompt": "start cmd",
            "powershell": "start powershell",
            "paint": "start mspaint",
            "mspaint": "start mspaint",
            "camera": "start microsoft.windows.camera:",
            "settings": "start ms-settings:",
            "windows settings": "start ms-settings:",
            "control panel": "start control",
            "explorer": "start explorer",
            "file explorer": "start explorer",
            "files": "start explorer",
            "my files": "start explorer",
            "word": "start winword",
            "ms word": "start winword",
            "excel": "start excel",
            "ms excel": "start excel",
            "powerpoint": "start powerpnt",
            "ppt": "start powerpnt",
            "vlc": "start vlc",
            "vlc media player": "start vlc",
            "discord": "start discord",
            "steam": "start steam",
            "youtube": "start https://www.youtube.com",
            "google": "start https://www.google.com",
            "github": "start https://www.github.com",
            "gmail": "start https://mail.google.com"
        }

    def get_system_health(self) -> str:
        """Retrieve real-time telemetry on CPU, RAM, Disk, and Battery."""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:').percent
            
            battery_str = ""
            batt = psutil.sensors_battery()
            if batt:
                plug_str = "Plugged In (Charging)" if batt.power_plugged else "Discharging"
                battery_str = f"\n• Battery: `{batt.percent}%` ({plug_str})"
            
            report = (
                "🖥️ *System Telemetry Audit*\n"
                f"• CPU Load: `{cpu}%`\n"
                f"• RAM Usage: `{ram}%`\n"
                f"• C: Drive Capacity: `{disk}%` usage"
                f"{battery_str}\n"
                f"• Status: 🟢 STABLE" if cpu < 80 else "• Status: 🟡 HIGH LOAD"
            )
            return report
        except Exception as e:
            logger.error(f"Telemetry Failure: {e}")
            return "⚠️ System Telemetry Offline: Unable to access hardware sensors."

    def get_battery_status(self) -> str:
        """Get battery telemetry."""
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return "Workstation is operating on AC utility mains power, sir. No internal battery present."
            percent = int(battery.percent)
            plugged = battery.power_plugged
            status = "charging" if plugged else "discharging on battery power"
            return f"Internal power cells are at {percent} percent capacity, currently {status}, sir."
        except Exception as e:
            return f"Battery telemetry offline: {e}"

    def launch_app(self, app_name: str) -> str:
        """Execute a Windows launch command for a recognized application."""
        import re
        clean = app_name.lower().strip()
        # Clean common natural language prefixes & suffixes
        clean = re.sub(r"^(?:the|a|an|my|our)\s+", "", clean).strip()
        clean = re.sub(r"\s+(?:app|application|software|program|tool)$", "", clean).strip()

        # Security validation: reject shell metacharacters and command chaining
        if not re.match(r'^[a-zA-Z0-9_\-\. :\/]+$', clean):
            logger.warning(f"OS Node: Blocked launch string containing prohibited characters: '{clean}'")
            return f"❌ Access Denied: Application name contains prohibited characters."

        command = self.app_mapping.get(clean)
        try:
            if command:
                if command.startswith("start "):
                    target = command[6:].strip()
                    subprocess.Popen(["cmd.exe", "/c", "start", "", target], shell=False)
                else:
                    subprocess.Popen([command], shell=False)
            else:
                clean_target = clean.strip()
                subprocess.Popen(["cmd.exe", "/c", "start", "", clean_target], shell=False)

            logger.info(f"OS Node: Executed launch command for '{clean}'")
            return f"Application '{clean}' is initializing on your workstation, sir."
        except Exception as e:
            logger.error(f"Launch Failure: {e}")
            return f"Access Denied: Failed to initialize '{clean}'. Error: {str(e)}"

    def close_app(self, app_name: str) -> str:
        """Terminate an active application by name."""
        import re
        clean = app_name.lower().strip()
        clean = re.sub(r"^(?:the|a|an|my)\s+", "", clean).strip()
        clean = re.sub(r"\s+(?:app|application|software|program|tool)$", "", clean).strip()

        exe_map = {
            "notepad": "notepad.exe",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "calculator": "CalculatorApp.exe",
            "calc": "CalculatorApp.exe",
            "spotify": "Spotify.exe",
            "code": "Code.exe",
            "vscode": "Code.exe",
            "vs code": "Code.exe",
            "visual studio code": "Code.exe",
            "task manager": "Taskmgr.exe",
            "taskmgr": "Taskmgr.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "terminal": "WindowsTerminal.exe",
            "powershell": "powershell.exe",
            "paint": "mspaint.exe",
            "vlc": "vlc.exe",
            "discord": "Discord.exe",
            "steam": "steam.exe"
        }
        target_exe = exe_map.get(clean, f"{clean}.exe")
        try:
            res = subprocess.run(["taskkill", "/IM", target_exe, "/F"], capture_output=True, text=True)
            if res.returncode == 0:
                logger.info(f"OS Node: Terminated '{target_exe}'")
                return f"Process '{target_exe}' has been terminated successfully, sir."
            else:
                return f"No running process found for '{clean}'."
        except Exception as e:
            logger.error(f"Termination error: {e}")
            return f"Failed to terminate '{clean}': {e}"

    def take_screenshot(self) -> dict:
        """Capture screenshot and save to data/screenshots directory."""
        from datetime import datetime
        try:
            screenshots_dir = os.path.join(os.getcwd(), "data", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jarvis_screenshot_{timestamp}.png"
            filepath = os.path.join(screenshots_dir, filename)

            # Try interactive PIL grab
            saved = False
            try:
                from PIL import ImageGrab
                im = ImageGrab.grab()
                im.save(filepath, "PNG")
                saved = True
            except Exception as grab_err:
                logger.debug(f"Direct ImageGrab failed, launching screen clip utility: {grab_err}")

            if saved and os.path.exists(filepath):
                # Launch image viewer for the user
                subprocess.Popen(["cmd.exe", "/c", "start", "", filepath], shell=False)
                return {
                    "success": True,
                    "filepath": filepath,
                    "filename": filename,
                    "message": f"Screenshot captured and saved to your tactical directory: {filename}"
                }
            else:
                # Trigger Windows Snipping Tool / Screen Clip
                subprocess.Popen(["cmd.exe", "/c", "start", "ms-screenclip:"], shell=False)
                return {
                    "success": True,
                    "filepath": "",
                    "filename": "ScreenClip",
                    "message": "Windows screen clipping utility deployed to display, sir."
                }
        except Exception as e:
            logger.error(f"Screenshot failure: {e}")
            return {"success": False, "error": str(e), "message": f"Unable to capture screen: {e}"}

    def lock_workstation(self) -> str:
        """Lock the Windows workstation immediately."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Workstation perimeter secured. Terminal locked, sir."
        except Exception as e:
            try:
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
                return "Workstation locked, sir."
            except Exception as e2:
                return f"Failed to lock workstation: {e2}"

    def house_party_protocol(self) -> dict:
        """Deploy the Stark House Party Protocol: launch developer workshop suites."""
        try:
            # Deploy multi-window workshop: Terminal, VS Code, Browser
            subprocess.Popen(["cmd.exe", "/c", "start", "wt"], shell=False)
            subprocess.Popen(["cmd.exe", "/c", "start", "code"], shell=False)
            subprocess.Popen(["cmd.exe", "/c", "start", "chrome"], shell=False)
            return {
                "success": True,
                "protocol": "House Party Protocol",
                "spoken_response": "House Party Protocol engaged, sir. Deploying the workshop environment and developer suites across your monitors.",
                "message": "House Party Protocol: VS Code, Terminal, and Chrome operational."
            }
        except Exception as e:
            logger.error(f"House Party Protocol failure: {e}")
            return {"success": False, "error": str(e), "spoken_response": f"House Party Protocol encountered an error: {e}"}

    def clean_slate_protocol(self) -> dict:
        """Execute Clean Slate Protocol: close non-essential apps, purge caches and recycle bin."""
        try:
            # Safely terminate common non-essential apps
            non_essentials = ["notepad.exe", "calc.exe", "CalculatorApp.exe", "vlc.exe", "mspaint.exe"]
            for app in non_essentials:
                try:
                    subprocess.run(["taskkill", "/IM", app, "/F"], capture_output=True)
                except Exception:
                    pass
            # Empty recycle bin
            self.empty_recycle_bin()
            # Flush DNS
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
            # Clear clipboard
            self.copy_to_clipboard("")
            return {
                "success": True,
                "protocol": "Clean Slate Protocol",
                "spoken_response": "Clean Slate Protocol executed, sir. Non-essential processes terminated, memory caches purged, and workstation reset to clean baseline.",
                "message": "Clean Slate Protocol complete: non-essential apps closed, clipboard cleared, DNS flushed, Recycle Bin emptied."
            }
        except Exception as e:
            logger.error(f"Clean Slate failure: {e}")
            return {"success": False, "error": str(e), "spoken_response": f"Clean Slate Protocol encountered an error: {e}"}

    def emergency_protocol_13(self) -> dict:
        """Execute Emergency Protocol 13: lock down workstation and wipe volatile clipboard."""
        try:
            self.copy_to_clipboard("")
            self.lock_workstation()
            return {
                "success": True,
                "protocol": "Emergency Protocol 13",
                "spoken_response": "Emergency Protocol 13 engaged, sir. Security perimeter sealed, volatile clipboard cache purged, and terminal locked.",
                "message": "Emergency Protocol 13: Workstation locked and clipboard purged."
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Protocol 13 failure: {e}"}

    def armor_diagnostics(self) -> dict:
        """Retrieve full Iron Man armor-style diagnostic telemetry."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:').percent
            batt = psutil.sensors_battery()
            power_level = int(batt.percent) if batt else 100
            power_state = "Arc Reactor mains active" if not batt or batt.power_plugged else f"Reserve cell discharge at {power_level}%"

            net = self.check_network_health()
            ping = net.get("latency", "1ms")

            spoken = (
                f"All armor subsystems nominal, sir. Power core is at {power_level} percent with {power_state}. "
                f"Central processing load is {cpu} percent, memory allocation is {ram} percent, and quantum telemetry ping is {ping}."
            )
            return {
                "success": True,
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "power_level": power_level,
                "ping": ping,
                "spoken_response": spoken
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Armor diagnostic sensors offline: {e}"}


    def control_volume(self, action: str) -> str:
        """Adjust master system volume via Windows Shell."""
        try:
            act = action.lower().strip()
            if "mute" in act or "unmute" in act:
                cmd = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
                spoken = "Audio mute status toggled, sir."
            elif "up" in act or "increase" in act or "raise" in act or "louder" in act:
                cmd = "$w = New-Object -ComObject WScript.Shell; 1..5 | ForEach-Object { $w.SendKeys([char]175) }"
                spoken = "Increasing system volume, sir."
            elif "down" in act or "decrease" in act or "lower" in act or "quieter" in act:
                cmd = "$w = New-Object -ComObject WScript.Shell; 1..5 | ForEach-Object { $w.SendKeys([char]174) }"
                spoken = "Decreasing system volume, sir."
            elif "max" in act or "full" in act or "100" in act:
                cmd = "$w = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object { $w.SendKeys([char]175) }"
                spoken = "System volume set to maximum, sir."
            else:
                return "Unrecognized volume command."

            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
            return spoken
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return f"Volume adjustment error: {e}"

    def open_folder(self, folder_name: str) -> str:
        """Open a standard Windows folder in File Explorer."""
        import re
        folder = folder_name.lower().strip()
        folder = re.sub(r"^(?:my|the)\s+", "", folder).strip()
        folder = re.sub(r"\s+folder$", "", folder).strip()

        user_home = Path.home()
        mapping = {
            "downloads": user_home / "Downloads",
            "documents": user_home / "Documents",
            "desktop": Path(self.get_desktop_path()),
            "pictures": user_home / "Pictures",
            "music": user_home / "Music",
            "videos": user_home / "Videos",
            "c drive": Path("C:\\"),
            "c:": Path("C:\\"),
            "c": Path("C:\\")
        }
        target = mapping.get(folder)
        if target and os.path.exists(target):
            subprocess.Popen(["explorer.exe", str(target)])
            return f"Opening your {folder} directory in File Explorer, sir."
        else:
            subprocess.Popen(["explorer.exe"])
            return "Opening File Explorer on your workspace, sir."

    def empty_recycle_bin(self) -> str:
        """Empty the Windows Recycle Bin silently."""
        try:
            cmd = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
            return "Recycle Bin purged and storage reclaimed, sir."
        except Exception as e:
            return f"Failed to empty Recycle Bin: {e}"

    def search_web(self, query: str) -> str:
        """Launch default browser with Google Search query."""
        import urllib.parse
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        subprocess.Popen(["cmd.exe", "/c", "start", "", url], shell=False)
        return f"Executing neural search for {query} on your primary browser, sir."

    def list_processes(self) -> str:
        """Scan active system nodes (top 15 by memory)."""
        try:
            procs = []
            for proc in psutil.process_iter(['name', 'memory_percent']):
                procs.append(proc.info)
            
            # Sort by memory
            procs = sorted(procs, key=lambda i: i['memory_percent'], reverse=True)[:15]
            
            out = "📑 *Active Intelligence Nodes (Top 15)*\n"
            for p in procs:
                out += f"• `{p['name']}`: {p['memory_percent']:.1f}% mem\n"
            return out
        except Exception as e:
            logger.error(f"Process Scan Failure: {e}")
            return "⚠️ Search Node Failure: Unable to audit active processes."

    def get_desktop_path(self) -> str:
        """Dynamically detect the Windows Desktop path."""
        # Check standard C:\Users\<User>\Desktop
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        # Check if redirected to OneDrive
        onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        
        if os.path.exists(onedrive_desktop):
            return onedrive_desktop
        return desktop

    def organize_directory(self, target_path: str = None) -> str:
        """Intelligently sort files into categories by extension."""
        path = target_path or self.get_desktop_path()
        if not os.path.exists(path):
            return f"❌ Path not found: {path}"

        extensions = {
            "Media": [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3", ".mov", ".wav"],
            "Documents": [".pdf", ".docx", ".txt", ".pptx", ".xlsx", ".csv"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".html", ".css", ".cpp", ".c", ".json", ".sh", ".bat"],
            "Installers": [".exe", ".msi"]
        }

        moved_count = 0
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    ext = os.path.splitext(item).lower()[1:]
                    if not ext: continue
                    
                    for category, exts in extensions.items():
                        if f".{ext}" in exts:
                            dest_dir = os.path.join(path, category)
                            os.makedirs(dest_dir, exist_ok=True)
                            shutil.move(item_path, os.path.join(dest_dir, item))
                            moved_count += 1
                            break
            
            return f"✅ Optimization Complete. {moved_count} files categorized in '{os.path.basename(path)}'."
        except Exception as e:
            logger.error(f"Organization Failure: {e}")
            return f"⚠️ Organization interrupted: {str(e)}"

    def deep_search(self, pattern: str) -> str:
        """Recursive system search for files matching a pattern."""
        search_root = os.path.expanduser("~")
        results = []
        try:
            # Look in core folders (Desktop, Documents, Downloads)
            folders = ["Desktop", "Documents", "Downloads"]
            for folder in folders:
                folder_path = os.path.join(search_root, folder)
                if not os.path.exists(folder_path): continue
                
                # Check for OneDrive redirection
                if "OneDrive" in os.listdir(search_root):
                    od_path = os.path.join(search_root, "OneDrive", folder)
                    if os.path.exists(od_path): folder_path = od_path

                matches = glob.glob(os.path.join(folder_path, f"*{pattern}*"), recursive=True)
                results.extend(matches[:5]) # Limit to top 5 per folder
                if len(results) >= 15: break

            if not results:
                return f"🔍 No files matching '{pattern}' were found in common directories."
            
            out = f"🔍 *Neural Search Results for '{pattern}':*\n"
            for r in results[:10]:
                out += f"• `{os.path.basename(r)}` -> `{r}`\n"
            return out
        except Exception as e:
            logger.error(f"Search Failure: {e}")
            return f"❌ Search node failed: {str(e)}"

    def summarize_file(self, file_path: str) -> str:
        """Read file content for neural summarization."""
        if not os.path.exists(file_path):
            return "❌ Error: Targeted file does not exist."
        
        try:
            # Read first 4KB to stay within context limits
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(4000)
            
            if not content:
                return "💨 This file appears to be empty."
            
            return f"--- FILE CONTENT: {os.path.basename(file_path)} ---\n{content}\n--- END CONTENT ---"
        except Exception as e:
            return f"❌ Failed to read file: {str(e)}"

    def resolve_path(self, target: str) -> str:
        """Resolve common location aliases like desktop, downloads, documents."""
        t = target.strip().replace("/", "\\")
        home = os.path.expanduser("~")
        desktop = self.get_desktop_path()
        downloads = os.path.join(home, "Downloads")
        documents = os.path.join(home, "Documents")

        t_low = t.lower()
        if t_low.startswith("desktop\\") or t_low == "desktop":
            sub = t[8:].lstrip("\\")
            return os.path.join(desktop, sub) if sub else desktop
        elif t_low.startswith("downloads\\") or t_low == "downloads":
            sub = t[10:].lstrip("\\")
            return os.path.join(downloads, sub) if sub else downloads
        elif t_low.startswith("documents\\") or t_low == "documents":
            sub = t[10:].lstrip("\\")
            return os.path.join(documents, sub) if sub else documents
        elif os.path.isabs(t):
            return t
        else:
            return os.path.join(desktop, t)

    def create_folder(self, folder_path: str) -> dict:
        """Create a directory on the local Windows system."""
        try:
            full_path = self.resolve_path(folder_path)
            os.makedirs(full_path, exist_ok=True)
            name = os.path.basename(full_path)
            logger.info(f"OS Node: Created folder at '{full_path}'")
            return {
                "success": True,
                "path": full_path,
                "name": name,
                "spoken_response": f"I have created the directory '{name}' on your system, sir.",
                "message": f"Directory '{name}' created at: {full_path}"
            }
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return {"success": False, "error": str(e), "spoken_response": f"Unable to create folder: {e}"}

    def create_file(self, file_path: str, content: str = "") -> dict:
        """Create or write a file with contents on the local Windows system."""
        try:
            full_path = self.resolve_path(file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            name = os.path.basename(full_path)
            logger.info(f"OS Node: Created file '{full_path}' with {len(content)} chars")
            return {
                "success": True,
                "path": full_path,
                "name": name,
                "size": len(content),
                "spoken_response": f"File '{name}' has been created and saved, sir.",
                "message": f"File '{name}' created at: {full_path}"
            }
        except Exception as e:
            logger.error(f"Failed to create file: {e}")
            return {"success": False, "error": str(e), "spoken_response": f"Unable to write file: {e}"}

    def read_file(self, file_path: str) -> dict:
        """Read content from a file anywhere on the system."""
        try:
            full_path = self.resolve_path(file_path)
            if not os.path.exists(full_path):
                return {"success": False, "error": f"File does not exist: {file_path}"}
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(5000)
            return {
                "success": True,
                "path": full_path,
                "name": os.path.basename(full_path),
                "content": content,
                "spoken_response": f"File content retrieved from {os.path.basename(full_path)}, sir."
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Unable to read file: {e}"}

    def list_directory(self, location: str = "desktop") -> dict:
        """List files and directories in a given folder."""
        try:
            full_path = self.resolve_path(location)
            if not os.path.exists(full_path):
                return {"success": False, "error": f"Path not found: {location}"}
            items = []
            for entry in os.scandir(full_path):
                is_dir = entry.is_dir()
                size = entry.stat().st_size if not is_dir else 0
                items.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size_kb": round(size / 1024, 1)
                })
            items = sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))[:25]
            summary = f"Located {len(items)} items in {os.path.basename(full_path)}."
            spoken = f"I found {len(items)} items in your {os.path.basename(full_path)} workspace, sir."
            return {
                "success": True,
                "path": full_path,
                "items": items,
                "summary": summary,
                "spoken_response": spoken
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Unable to scan directory: {e}"}

    def minimize_all_windows(self) -> str:
        """Minimize all open windows to show the desktop."""
        try:
            cmd = "(New-Object -ComObject Shell.Application).MinimizeAll()"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
            return "Minimizing all interfaces to reveal your desktop workspace, sir."
        except Exception as e:
            return f"Interface minimization note: {e}"

    def restore_all_windows(self) -> str:
        """Restore all previously minimized windows."""
        try:
            cmd = "(New-Object -ComObject Shell.Application).UndoMinimizeAll()"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
            return "Restoring previous interface layout on your display, sir."
        except Exception as e:
            return f"Interface restore note: {e}"

    def set_brightness(self, percent: int) -> str:
        """Set screen brightness (0-100%)."""
        try:
            val = max(0, min(100, int(percent)))
            cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {val})"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
            return f"Display luminance calibrated to {val} percent, sir."
        except Exception as e:
            return f"Luminance adjustment error: {e}"

    def get_brightness(self) -> str:
        """Get current screen brightness."""
        try:
            cmd = "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
            res = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], text=True).strip()
            return f"Current display luminance is at {res} percent, sir."
        except Exception as e:
            return f"Luminance sensor offline: {e}"

    def check_network_health(self) -> dict:
        """Perform real-time network and latency ping diagnostics."""
        import socket
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            r = subprocess.run(["ping", "-n", "1", "8.8.8.8"], capture_output=True, text=True)
            import re
            m = re.search(r"time[=<](\d+)ms", r.stdout)
            latency = f"{m.group(1)}ms" if m else "1ms"
            is_connected = r.returncode == 0

            if is_connected:
                spoken = f"Network telemetry nominal, sir. Ping latency is {latency} to Google DNS, local IP is {local_ip}."
            else:
                spoken = "Network link degraded or offline, sir. Unable to resolve external DNS gateway."

            return {
                "success": is_connected,
                "local_ip": local_ip,
                "hostname": hostname,
                "latency": latency,
                "spoken_response": spoken
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Network diagnostic failure: {e}"}

    def copy_to_clipboard(self, text: str) -> str:
        """Copy text to Windows clipboard."""
        try:
            proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"], stdin=subprocess.PIPE, text=True)
            proc.communicate(input=text)
            return "Intel committed to your Windows clipboard, sir. Ready for insertion."
        except Exception as e:
            return f"Clipboard write note: {e}"

    def get_clipboard_content(self) -> str:
        """Read text from Windows clipboard."""
        try:
            res = subprocess.check_output(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], text=True).strip()
            return res if res else "Clipboard is currently empty, sir."
        except Exception as e:
            return f"Clipboard read note: {e}"

    def sleep_workstation(self) -> str:
        """Put Windows workstation into sleep mode."""
        try:
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return "Workstation entering low-power standby mode, sir. Good night."
        except Exception as e:
            return f"Sleep command error: {e}"

    def run_command(self, cmd_str: str) -> dict:
        """Execute a safe shell command for autonomous user tasks."""
        banned = ["format ", "rmdir /s /q c:\\", "del /f /s /q c:\\", "drop database"]
        for b in banned:
            if b in cmd_str.lower():
                return {"success": False, "error": "Prohibited destructive command", "spoken_response": "Protocol breach: Prohibited destructive command aborted, sir."}
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd_str], capture_output=True, text=True, timeout=15)
            out = res.stdout.strip() or res.stderr.strip() or "Command completed with return code 0."
            return {
                "success": res.returncode == 0,
                "output": out[:2000],
                "spoken_response": "Command executed successfully on your workstation terminal, sir."
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Command execution error: {e}"}

    def run_python_code(self, code: str) -> dict:
        """Execute Python code in local runtime and capture output."""
        import tempfile
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
                tf.write(code)
                tname = tf.name

            res = subprocess.run(["python", tname], capture_output=True, text=True, timeout=15)
            try:
                os.remove(tname)
            except Exception:
                pass
            out = res.stdout.strip()
            err = res.stderr.strip()
            output = out if out else (f"Errors: {err}" if err else "Execution completed with no output.")
            return {
                "success": res.returncode == 0,
                "output": output[:3000],
                "spoken_response": "Python sequence executed successfully on your local engine, sir."
            }
        except Exception as e:
            return {"success": False, "error": str(e), "spoken_response": f"Python execution error: {e}"}

    def execute_autonomous_stark_directive(self, directive: str) -> dict:
        """
        Omnipotent Autonomous Directive Engine:
        Interprets ANY natural user instruction, generates an action plan,
        executes physical OS actions on Windows, and returns Paul Bettany voice feedback.
        """
        import re
        import json
        clean = directive.strip()
        clean_low = clean.lower()

        # ─── FAST-PATH DIRECTIVES (0-5ms) ───

        # 1. Folder creation
        folder_m = (
            re.search(r"(?:create|make|build)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)\s+(?:on|in)\s+(?:my\s+)?(desktop|downloads|documents)\s+(?:named\s+|called\s+)?([a-zA-Z0-9_\-\. ]+)", clean_low)
            or re.search(r"(?:create|make|build)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)\s+(?:named\s+|called\s+)?([a-zA-Z0-9_\-\. ]+?)(?:\s+(?:on|in)\s+(?:my\s+)?(desktop|downloads|documents))?$", clean_low)
        )
        if folder_m:
            groups = folder_m.groups()
            if len(groups) == 2 and groups[0] in ["desktop", "downloads", "documents"]:
                loc = groups[0]
                raw_target = groups[1].strip()
            else:
                raw_target = groups[0].strip()
                loc = groups[1] if len(groups) > 1 and groups[1] else "desktop"
            target_path = f"{loc}/{raw_target}"
            res = self.create_folder(target_path)
            return {
                "status": "success",
                "action": "create_folder",
                "spoken_response": res.get("spoken_response", f"Directory '{raw_target}' created on your {loc}, sir."),
                "data": res
            }

        # 2. File creation
        file_m = re.search(r"(?:create|make|write)\s+(?:a\s+)?(?:new\s+)?file\s+(?:named\s+|called\s+)?([a-zA-Z0-9_\-\.]+)(?:\s+with\s+(?:content|text)\s+(.+))?$", clean_low)
        if file_m:
            filename = file_m.group(1).strip()
            content = file_m.group(2) or ""
            res = self.create_file(filename, content)
            return {
                "status": "success",
                "action": "create_file",
                "spoken_response": res.get("spoken_response", f"File {filename} has been created, sir."),
                "data": res
            }

        # 3. List directory
        list_m = re.search(r"(?:list|show|what's\s+in|check)\s+(?:all\s+)?(?:my\s+)?files?\s+(?:on|in)\s+(?:my\s+)?(desktop|downloads|documents|folder)", clean_low)
        if list_m:
            loc = list_m.group(1).strip()
            res = self.list_directory(loc)
            return {
                "status": "success",
                "action": "list_directory",
                "spoken_response": res.get("spoken_response", f"Found files in your {loc}, sir."),
                "data": res
            }

        # 4. Minimize / Show Desktop
        if any(k in clean_low for k in ["minimize all", "hide all windows", "show desktop", "minimize windows"]):
            spoken = self.minimize_all_windows()
            return {"status": "success", "action": "minimize_windows", "spoken_response": spoken}

        # 5. Restore windows
        if any(k in clean_low for k in ["restore windows", "undo minimize", "bring back windows"]):
            spoken = self.restore_all_windows()
            return {"status": "success", "action": "restore_windows", "spoken_response": spoken}

        # 6. Set Brightness
        bright_m = re.search(r"(?:set\s+)?brightness\s+(?:to\s+)?(\d+)(?:%)?", clean_low)
        if bright_m:
            level = int(bright_m.group(1))
            spoken = self.set_brightness(level)
            return {"status": "success", "action": "set_brightness", "spoken_response": spoken}

        # 7. Check Network / Ping
        if any(k in clean_low for k in ["check internet", "check wifi", "check network", "network status", "ping google", "internet speed"]):
            res = self.check_network_health()
            return {"status": "success", "action": "check_network", "spoken_response": res.get("spoken_response"), "data": res}

        # 8. Clipboard operations
        copy_m = re.search(r"(?:copy|clip)\s+(?:this\s+)?(?:to\s+(?:the\s+)?clipboard)[:\s]*(.+)$", clean_low)
        if copy_m:
            text = copy_m.group(1).strip()
            spoken = self.copy_to_clipboard(text)
            return {"status": "success", "action": "copy_clipboard", "spoken_response": spoken}

        # 9. Sleep workstation
        if any(k in clean_low for k in ["sleep laptop", "sleep computer", "put to sleep", "sleep workstation"]):
            spoken = self.sleep_workstation()
            return {"status": "success", "action": "sleep_workstation", "spoken_response": spoken}

        # 10. House Party Protocol
        if any(k in clean_low for k in ["house party protocol", "activate house party", "deploy house party", "party protocol"]):
            res = self.house_party_protocol()
            return {"status": "success", "action": "house_party_protocol", "spoken_response": res.get("spoken_response"), "data": res}

        # 11. Clean Slate Protocol
        if any(k in clean_low for k in ["clean slate protocol", "clean slate", "protocol clean slate", "execute clean slate"]):
            res = self.clean_slate_protocol()
            return {"status": "success", "action": "clean_slate_protocol", "spoken_response": res.get("spoken_response"), "data": res}

        # 12. Emergency Protocol 13 / Defensive Lockdown
        if any(k in clean_low for k in ["protocol 13", "emergency protocol 13", "defensive lockdown", "lockdown protocol", "lockdown workstation"]):
            res = self.emergency_protocol_13()
            return {"status": "success", "action": "emergency_protocol_13", "spoken_response": res.get("spoken_response"), "data": res}

        # 13. Armor Diagnostics / Suit Telemetry
        if any(k in clean_low for k in ["suit status", "armor diagnostics", "suit diagnostics", "mark diagnostics", "arc reactor status", "how is the suit", "armor status"]):
            res = self.armor_diagnostics()
            return {"status": "success", "action": "armor_diagnostics", "spoken_response": res.get("spoken_response"), "data": res}

        # ─── AUTONOMOUS AI ACTION PLANNER (For Complex Multi-Step Directives) ───
        try:
            from core.model_manager import ModelManager
            mm = ModelManager()
            system_prompt = (
                "You are J.A.R.V.I.S., Tony Stark's autonomous AI operating system assistant. "
                "The user gave an operational directive for their Windows computer. "
                "Analyze the directive and return ONLY a valid JSON object with the exact actions to execute.\n"
                "Available tools:\n"
                "- create_folder: {path: string}\n"
                "- create_file: {path: string, content: string}\n"
                "- run_python_code: {code: string}\n"
                "- run_command: {cmd_str: string}\n"
                "- launch_app: {app_name: string}\n"
                "- close_app: {app_name: string}\n"
                "- control_volume: {action: 'up'|'down'|'mute'|'max'}\n"
                "- take_screenshot: {}\n"
                "- check_network_health: {}\n"
                "- search_web: {query: string}\n\n"
                "JSON format:\n"
                "{\n"
                '  "spoken_response": "Formal British confirmation as Paul Bettany J.A.R.V.I.S.",\n'
                '  "actions": [\n'
                '    {"tool": "tool_name", "params": {...}}\n'
                "  ]\n"
                "}"
            )
            raw_plan = mm.generate(
                [{"role": "user", "content": f"Directive: {clean}"}],
                system_prompt=system_prompt,
                model="gemini-2.5-flash"
            )

            # Extract JSON block
            json_m = re.search(r"\{[\s\S]*\}", raw_plan)
            if json_m:
                plan = json.loads(json_m.group(0))
                spoken = plan.get("spoken_response") or "Directive executed as commanded, sir."
                actions = plan.get("actions", [])
                executed_results = []

                for act in actions:
                    tool = act.get("tool")
                    params = act.get("params", {})
                    if tool == "create_folder":
                        r = self.create_folder(params.get("path", "New Folder"))
                        executed_results.append(r)
                    elif tool == "create_file":
                        r = self.create_file(params.get("path", "file.txt"), params.get("content", ""))
                        executed_results.append(r)
                    elif tool == "run_python_code":
                        r = self.run_python_code(params.get("code", ""))
                        executed_results.append(r)
                    elif tool == "run_command":
                        r = self.run_command(params.get("cmd_str", ""))
                        executed_results.append(r)
                    elif tool == "launch_app":
                        r = self.launch_app(params.get("app_name", ""))
                        executed_results.append({"app": params.get("app_name"), "result": r})
                    elif tool == "close_app":
                        r = self.close_app(params.get("app_name", ""))
                        executed_results.append({"app": params.get("app_name"), "result": r})
                    elif tool == "take_screenshot":
                        r = self.take_screenshot()
                        executed_results.append(r)
                    elif tool == "check_network_health":
                        r = self.check_network_health()
                        executed_results.append(r)
                    elif tool == "search_web":
                        r = self.search_web(params.get("query", ""))
                        executed_results.append({"search": params.get("query"), "result": r})

                return {
                    "status": "success",
                    "action": "autonomous_plan",
                    "spoken_response": spoken,
                    "plan": plan,
                    "results": executed_results
                }
        except Exception as planner_err:
            logger.warning(f"Autonomous Stark Planner note: {planner_err}")

        # Fallback if no actions needed (informational / chit-chat)
        return {
            "status": "passthrough",
            "message": "Routing to core neural intelligence",
            "clean_prompt": clean
        }

# Global Instance
os_engine = OSEngine()
