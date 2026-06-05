"""
Telegram Bot Loop
Main listener for the remote access interface.
"""
import time
import os
import pathlib

# Try to import telebot
try:
    import telebot
except ImportError:
    print("[ERROR] pyTelegramBotAPI not found. Run: pip install pyTelegramBotAPI")
    sys.exit(1)

from auth_manager import AuthManager
from command_router import CommandRouter
from media_handler import MediaHandler

from dotenv import load_dotenv
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

if not TOKEN:
    print("[ERROR] TELEGRAM_BOT_TOKEN missing in .env")
    exit()

bot = telebot.TeleBot(TOKEN)
auth = AuthManager()
router = CommandRouter()
media = MediaHandler()

@bot.message_handler(commands=['start', 'status', 'screenshot', 'memory', 'vision', 'search'])
def handle_commands(message):
    if not auth.is_authorized(message.from_user.id):
        bot.reply_to(message, "🔒 Unauthorized access attempt logged.")
        return
        
    command = message.text.split()[0]
    print(f"[TELEGRAM] Admin executed: {command}")
    
    result = router.process(command=command, message_text=message.text)
    
    if result["type"] == "text":
        bot.reply_to(message, result["content"])
    elif result["type"] == "photo":
        with open(result["content"], "rb") as photo:
            bot.send_photo(message.chat.id, photo)
        # Clean up screenshot
        os.remove(result["content"])

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not auth.is_authorized(message.from_user.id):
        return
        
    print("[TELEGRAM] Received Voice Note.")
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    file_path = f"voice_note_{message.message_id}.ogg"
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)
        
    msg = bot.reply_to(message, "🎙️ Processing voice note...")
    
    # Transcribe
    text = media.transcribe_voice_note(file_path)
    print(f"[TELEGRAM] Transcribed: {text}")
    
    # Process with JARVIS Brain
    result = router.process(command="chat", message_text=text)
    
    bot.edit_message_text(f"🗣️ **You:** {text}\n\n🤖 **JARVIS:** {result['content']}", 
                          chat_id=message.chat.id, 
                          message_id=msg.message_id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not auth.is_authorized(message.from_user.id):
        bot.reply_to(message, "🔒 Unauthorized access attempt logged.")
        return
        
    print(f"[TELEGRAM] Admin says: {message.text}")
    result = router.process(command="chat", message_text=message.text)
    bot.reply_to(message, result["content"])

def start_bot():
    print("\n=======================================================")
    print("      JARVIS TELEGRAM REMOTE INTERFACE ACTIVE          ")
    print("=======================================================")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"[TELEGRAM] Connection error: {e}. Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()
