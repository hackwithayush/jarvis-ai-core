"""
Notifications
Allows JARVIS or background daemons to actively push messages to Telegram.
"""
import telebot
import os
import pathlib
from dotenv import load_dotenv

class NotificationManager:
    def __init__(self):
        # Load environment variables
        env_path = pathlib.Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)
        
        # Priority: TELEGRAM_BOT_TOKEN > BOT_TOKEN > dummy
        token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN") or "dummy:dummy"
        
        # Ensure token has a colon to prevent ValueError in telebot
        if ":" not in token:
            token = "dummy:dummy"
            
        self.bot = telebot.TeleBot(token)
        admin_ids = os.environ.get("ADMIN_TELEGRAM_IDS", "")
        self.primary_admin = int(admin_ids.split(",")[0]) if admin_ids else None
        
    def send_alert(self, message: str):
        """ Actively pushes a message to the admin without them asking. """
        if self.primary_admin:
            try:
                self.bot.send_message(self.primary_admin, f"⚠️ **JARVIS ALERT:**\n{message}")
                print(f"[NOTIFY] Alert pushed to admin: {message}")
            except Exception as e:
                print(f"[TELEGRAM] Failed to send alert: {e}")
