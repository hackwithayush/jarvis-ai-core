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
            "edge": "start msedge",
            "notepad": "start notepad",
            "code": "code",
            "vs code": "code",
            "spotify": "start spotify",
            "calculator": "start calc",
            "task manager": "start taskmgr",
            "terminal": "start wt",
            "cmd": "start cmd",
            "powershell": "start powershell"
        }

    def get_system_health(self) -> str:
        """Retrieve real-time telemetry on CPU, RAM, and Disk."""
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:').percent
            
            # Formating like a HUD report
            report = (
                "🖥️ *System Telemetry Audit*\n"
                f"• CPU Load: `{cpu}%`\n"
                f"• RAM Usage: `{ram}%`\n"
                f"• C: Drive Capacity: `{disk}%` usage\n"
                "• Status: 🟢 STABLE" if cpu < 80 else "• Status: 🟡 HIGH LOAD"
            )
            return report
        except Exception as e:
            logger.error(f"Telemetry Failure: {e}")
            return "⚠️ System Telemetry Offline: Unable to access hardware sensors."

    def launch_app(self, app_name: str) -> str:
        """Execute a Windows launch command for a recognized application."""
        app_name = app_name.lower().strip()
        command = self.app_mapping.get(app_name)
        
        if not command:
            # Try a generic start if not in mapping (risky, but useful)
            # We restrict this for safety in the agent layer, but here is the raw executor
            command = f"start {app_name}"

        try:
            # Using shell=True for 'start' commands on Windows
            subprocess.Popen(command, shell=True)
            logger.info(f"OS Node: Executed launch command for '{app_name}'")
            return f"✅ Intelligence relayed. Application '{app_name}' is initializing."
        except Exception as e:
            logger.error(f"Launch Failure: {e}")
            return f"❌ Access Denied: Failed to initialize '{app_name}'. Error: {str(e)}"

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

# Global Instance
os_engine = OSEngine()
