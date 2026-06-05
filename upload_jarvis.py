import os
import subprocess
import getpass

def run_git():
    print("🚀 JARVIS: Initializing Cloud Synchronization...")
    
    # Ensure we are in a git repo
    if not os.path.exists(".git"):
        subprocess.run(["git", "init"])

    # Configure user if not set
    subprocess.run(["git", "config", "user.email", "ayush@stark.com"])
    subprocess.run(["git", "config", "user.name", "Ayush Stark"])

    repo_url = "https://github.com/hackwithayush/jarvis-ai-core.git"
    
    print("\n🔑 SECURITY CHECK: Please PASTE your GitHub Token.")
    token = input("Token: ").strip()
    
    # Re-construct URL with token for auth
    auth_url = repo_url.replace("https://", f"https://hackwithayush:{token}@")

    print("\n⚡ Synchronizing folders (core, templates, static)...")
    subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "remote", "add", "origin", auth_url])
    subprocess.run(["git", "branch", "-M", "main"])
    
    subprocess.run(["git", "add", "core", "templates", "static", "app.py", "requirements.txt", "models.py", "telegram_bot.py", "config.py"])
    subprocess.run(["git", "commit", "-m", "JARVIS PRO: Full Neural Core + Vibranium HUD Upload"])
    
    print("\n🛰️ Pushing to Global Cloud...")
    result = subprocess.run(["git", "push", "-u", "origin", "main", "--force"])

    if result.returncode == 0:
        print("\n✅ SYSTEM ONLINE: Jarvis is now in the cloud. Check Render now!")
    else:
        print("\n❌ SYNC FAILURE: Check your token permissions or internet connection.")

if __name__ == "__main__":
    run_git()
