"""
Auth Manager
Ensures only the admin can access JARVIS remotely via Telegram.
"""
import os

class AuthManager:
    def __init__(self):
        # Comma separated list of Authorized User IDs
        admin_ids = os.environ.get("ADMIN_TELEGRAM_IDS", "123456789")
        self.admins = [int(x.strip()) for x in admin_ids.split(",") if x.strip()]
        print(f"[AUTH] Registered {len(self.admins)} authorized admin IDs.")
        
    def is_authorized(self, user_id: int) -> bool:
        """ Returns true if user is in the authorized admin list. """
        if user_id in self.admins:
            return True
        return False
