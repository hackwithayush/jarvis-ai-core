"""
Jarvis Telegram Bot — Pro Edition
Professional AI assistant with scheduling, search commands, and persistent memory.
"""
import sys
import os
import logging
import asyncio
import json
import uuid
from datetime import time, datetime, timezone

# Neural Pathing: Fix for cloud module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask

try:
    from telegram import Update, constants
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.error("Telegram Node Offline: 'python-telegram-bot' not found. Telegram features disabled.")
    # Mock classes to prevent NameErrors in type hints
    class Update: pass
    class ContextTypes:
        class DEFAULT_TYPE: pass
    class constants:
        class ParseMode: HTML = "HTML"
    class filters:
        TEXT = None; COMMAND = None; PHOTO = None; VOICE = None

import config
from core.model_manager import ModelManager
from core.knowledge_manager import KnowledgeManager
from core.chat_engine import ChatEngine
from core.agent_engine import AgentEngine
from core.brain import JarvisBrain
from core.voice_engine import VoiceEngine
from core.recommender import EntertainmentRecommender
from core.cache import global_cache 
from core.instagram_engine import InstagramEngine

# ─── Logging ─────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/telegram_bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("jarvis.pro")

# ─── Globals ─────────────────────────────────────────────────────
model_manager: ModelManager = None
knowledge_manager: KnowledgeManager = None
chat_engine: ChatEngine = None
agent_engine: AgentEngine = None
brain: JarvisBrain = None
flask_app: Flask = None
voice_engine: VoiceEngine = None
recommender: EntertainmentRecommender = None
instagram_engine: InstagramEngine = None

SUBS_FILE = "data/subscriptions.json"
processing_semaphore = asyncio.Semaphore(10) # 10 users at same time

# ─── Initialization ──────────────────────────────────────────────

def init_jarvis():
    """Initialize the Jarvis engine stack."""
    global model_manager, knowledge_manager, chat_engine, agent_engine, brain, flask_app, voice_engine, recommender, instagram_engine

    logger.info("Initializing Jarvis Pro Engine...")
    model_manager = ModelManager()
    knowledge_manager = KnowledgeManager()
    chat_engine = ChatEngine(model_manager, knowledge_manager)
    agent_engine = AgentEngine()
    brain = JarvisBrain(agent_engine)
    voice_engine = VoiceEngine()
    recommender = EntertainmentRecommender()
    instagram_engine = InstagramEngine()
    
    # ─── Database & Storage ─────────────────────────────────────
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Initialize DB (Telegram standalone mode)
    flask_app = Flask(__name__)
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    from models import db, User
    db.init_app(flask_app)
    
    with flask_app.app_context():
        db.create_all()
        # Enforce Default Identity if missing
        if not User.query.filter_by(username='Admin').first():
            admin = User(username='Admin', email='admin@local.host')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            logger.info("✓ Primary Database initialized.")

    if not os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, "w") as f:
            json.dump({"subscribers": []}, f)

    logger.info("Jarvis Pro Engine — ONLINE")

# ─── Subscription Helpers ────────────────────────────────────────

def get_subs():
    try:
        with open(SUBS_FILE, "r") as f:
            return set(json.load(f).get("subscribers", []))
    except Exception:
        return set()

def save_subs(subs):
    with open(SUBS_FILE, "w") as f:
        json.dump({"subscribers": list(subs)}, f)

# ─── Neural Memory Helpers ────────────────────────────────────────

def get_db_user(telegram_id):
    """Get or create a DB user from Telegram ID."""
    from models import db, User
    with flask_app.app_context():
        username = f"tg_{telegram_id}"
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, email=f"{username}@telegram.local")
            user.set_password(str(telegram_id))
            db.session.add(user)
            db.session.commit()
        return user

def update_user_taste(telegram_id, category):
    """Update and persist user entertainment preferences."""
    from models import db, User
    with flask_app.app_context():
        username = f"tg_{telegram_id}"
        user = User.query.filter_by(username=username).first()
        if not user: return
        
        prefs = user.preferences or {}
        history = prefs.get("entertainment_taste", [])
        history.append(category)
        
        # Limit memory to last 20 interests
        prefs["entertainment_taste"] = history[-20:]
        user.preferences = prefs
        
        db.session.add(user)
        db.session.commit()
        logger.info(f"✓ Taste Synced: {username} -> {category.upper()}")

# ─── Command Handlers ────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Professional welcome message."""
    welcome_text = (
        "🤖 *Jarvis Pro Online*\n\n"
        "Welcome, Stark. I am your personal AI assistant, powered by the latest intelligence nodes.\n\n"
        "*Available Commands:*\n"
        "💬 *Chat* — Just type normally to talk.\n"
        "🖼️ `/image <prompt>` — Generate Art.\n"
        "🎬 `/video <prompt>` — Create AI Video.\n"
        "🔍 `/search <query>` — Targeted web search.\n"
        "📰 `/news <topic>` — Latest news updates.\n"
        "📅 `/subscribe` — Receive daily news at 9:00 AM.\n"
        "🔄 `/new` — Start a fresh mental state.\n\n"
        "_Tip: Send a photo with a caption like 'make it cyberpunk' to edit it!_"
        "_How can I help you today?_"
    )
    await update.message.reply_text(welcome_text, parse_mode=constants.ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed help menu."""
    help_text = (
        "🚀 *Jarvis Professional Help*\n\n"
        "I am designed to be fast, smart, and adaptive.\n\n"
        "*Usage Tips:*\n"
        "• *Memory*: I remember our past conversations automatically.\n"
        "• *Tools*: I can search the web, read files, and run code if you ask me to.\n"
        "• *News*: Use `/news technology` for specific updates.\n\n"
        "For system issues, contact your administrator (Ayush Stark)."
    )
    await update.message.reply_text(help_text, parse_mode=constants.ParseMode.MARKDOWN)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit search command."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("🔍 *Usage*: `/search latest space x launch`", parse_mode=constants.ParseMode.MARKDOWN)
        return

    await update.message.reply_text(f"🔎 *Searching for*: _{query}_...", parse_mode=constants.ParseMode.MARKDOWN)
    await handle_message(update, context, forced_message=f"search {query}")

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit image generation command."""
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("🖼️ *Usage*: `/image a futuristic city`", parse_mode=constants.ParseMode.MARKDOWN)
        return

    await update.message.reply_text(f"🎨 *Synthesizing*: _{prompt}_...", parse_mode=constants.ParseMode.MARKDOWN)
    await handle_message(update, context, forced_message=f"generate image {prompt}")

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit video generation command."""
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("🎬 *Usage*: `/video iron man flying`", parse_mode=constants.ParseMode.MARKDOWN)
        return

    await update.message.reply_text("🎬 *Initializing Video Node...*", parse_mode=constants.ParseMode.MARKDOWN)
    await handle_message(update, context, forced_message=f"create video {prompt}")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicit news command."""
    topic = " ".join(context.args) or "general"
    await update.message.reply_text(f"📰 *Fetching updates on*: _{topic}_...", parse_mode=constants.ParseMode.MARKDOWN)
    await handle_message(update, context, forced_message=f"latest news about {topic}")

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to daily news."""
    chat_id = update.effective_chat.id
    subs = get_subs()
    if chat_id in subs:
        await update.message.reply_text("✅ You are already subscribed to daily updates.")
    else:
        subs.add(chat_id)
        save_subs(subs)
        await update.message.reply_text("🔔 *Subscribed!* You will receive daily news updates at 9:00 AM.", parse_mode=constants.ParseMode.MARKDOWN)

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from daily news."""
    chat_id = update.effective_chat.id
    subs = get_subs()
    if chat_id in subs:
        subs.remove(chat_id)
        save_subs(subs)
        await update.message.reply_text("🔕 *Unsubscribed.* You will no longer receive daily updates.", parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("You are not currently subscribed.")

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle voice mode."""
    if not context.args:
        current = context.user_data.get("voice_mode", False)
        status = "ON" if current else "OFF"
        await update.message.reply_text(f"🎙️ *Voice Mode*: `{status}`\nUse `/voice on` or `/voice off` to change.", parse_mode=constants.ParseMode.MARKDOWN)
        return

    mode = context.args[0].lower()
    if mode == "on":
        context.user_data["voice_mode"] = True
        await update.message.reply_text("🔊 *Voice Mode Enabled.* Jarvis will now speak his replies.", parse_mode=constants.ParseMode.MARKDOWN)
    elif mode == "off":
        context.user_data["voice_mode"] = False
        await update.message.reply_text("🔈 *Voice Mode Disabled.* Back to silent text operations.", parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("🔍 Usage: `/voice on` or `/voice off`", parse_mode=constants.ParseMode.MARKDOWN)

async def nudge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger the Mission Auditor for a status update."""
    await update.message.reply_text("🎯 *Scanning Mission Grid...*", parse_mode=constants.ParseMode.MARKDOWN)
    await audit_missions(context)

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch personality mode."""
    if not context.args:
        current = context.user_data.get("personality", "normal")
        modes = ", ".join([f"`{m}`" for m in config.PERSONALITY_PROMPTS.keys()])
        await update.message.reply_text(f"😎 *Active Mode*: `{current}`\nAvailable: {modes}\n\nUse `/mode savage` to switch.", parse_mode=constants.ParseMode.MARKDOWN)
        return

    new_mode = context.args[0].lower()
    if new_mode in config.PERSONALITY_PROMPTS:
        context.user_data["personality"] = new_mode
        await update.message.reply_text(f"🔥 *Personality Synced*: `{new_mode}` mode active node.", parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ Invalid mode. Available: {', '.join(config.PERSONALITY_PROMPTS.keys())}")

async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a fresh conversation."""
    user_id = str(update.effective_user.id)
    chat_engine.new_conversation(conv_id=f"tg_{user_id}", title=f"Telegram-{user_id}")
    await update.message.reply_text("🔄 *Memory Flushed.* My mental state is fresh and ready.", parse_mode=constants.ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive system diagnostics (Ollama + OS)."""
    from core.os_engine import os_engine
    
    # 1. AI Logic Status
    ai_status = model_manager.get_status()
    ollama_status = "🟢 ON" if ai_status["ollama_running"] else "🔴 OFF"
    
    # 2. OS Health Status
    os_report = os_engine.get_system_health()
    
    diag_text = (
        f"🤖 *Intelligence Logic Status*\n"
        f"• Ollama Core: {ollama_status}\n"
        f"• Active Model: `{ai_status['current_model']}`\n"
        f"• Neural Path: `{config.OLLAMA_HOST}`\n\n"
        f"{os_report}\n\n"
        f"• *Subscribers*: `{len(get_subs())}`"
    )
    await update.message.reply_text(diag_text, parse_mode=constants.ParseMode.MARKDOWN)

async def open_app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually launch a PC application."""
    if not context.args:
        await update.message.reply_text("🚀 *Usage*: `/open chrome` or `/open notepad`", parse_mode=constants.ParseMode.MARKDOWN)
        return
    
    app_name = " ".join(context.args)
    from core.os_engine import os_engine
    result = os_engine.launch_app(app_name)
    await update.message.reply_text(result, parse_mode=constants.ParseMode.MARKDOWN)

# ─── Instagram Creator Hub ───────────────────────────────────────

async def ig_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze recent posts for growth insights."""
    await update.message.reply_text("📊 *Scanning Instagram Grid...*", parse_mode=constants.ParseMode.MARKDOWN)
    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, instagram_engine.analyze_performance)
    await update.message.reply_text(res, parse_mode=constants.ParseMode.MARKDOWN)

async def ig_ideas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate viral anime content ideas."""
    await update.message.reply_text("💡 *Synthesizing Viral Concepts...*", parse_mode=constants.ParseMode.MARKDOWN)
    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, instagram_engine.generate_viral_ideas)
    await update.message.reply_text(res, parse_mode=constants.ParseMode.MARKDOWN)

async def ig_caption_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Draft a caption with hashtags."""
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("📝 *Usage*: `/ig_caption <topic>` (e.g., /ig_caption Sukuna edit)", parse_mode=constants.ParseMode.MARKDOWN)
        return
    await update.message.reply_text("✍️ *Drafting neural caption...*", parse_mode=constants.ParseMode.MARKDOWN)
    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, lambda: instagram_engine.draft_caption(topic))
    await update.message.reply_text(res, parse_mode=constants.ParseMode.MARKDOWN)

# ─── Vision Handler ──────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming images via Vision AI or Image Editing AI."""
    user_id = str(update.effective_user.id)
    caption = update.message.caption or ""
    
    photo_file = await update.message.photo[-1].get_file()
    img_path = os.path.join(config.DATA_DIR, f"tg_input_{user_id}.png")
    await photo_file.download_to_drive(img_path)
    
    await update.message.chat.send_action(constants.ChatAction.TYPING)
    
    # Check if user wants to EDIT or ANALYZE
    is_edit_intent = any(kw in caption.lower() for kw in ["edit", "change", "modify", "make it", "style", "transform"])
    
    try:
        if is_edit_intent:
            await update.message.reply_text("✏️ *Editing image...*", parse_mode=constants.ParseMode.MARKDOWN)
            # Use the agent to handle the edit logic
            await handle_message(update, context, forced_message=f"edit image {caption}")
        else:
            await update.message.reply_text("👁️ *Analyzing image...*", parse_mode=constants.ParseMode.MARKDOWN)
            loop = asyncio.get_running_loop()
            analysis = await loop.run_in_executor(
                None, lambda: model_manager.generate_vision(caption or "What is this?", img_path)
            )
            await update.message.reply_text(f"🤖 *Vision Report:*\n\n{analysis}", parse_mode=constants.ParseMode.MARKDOWN)
            
        # Cleanup input after processing
        # if os.path.exists(img_path): os.remove(img_path)
            
    except Exception as e:
        logger.error(f"Media handler error: {e}")
        await update.message.reply_text("⚠️ Intelligence Interface failure. Failed to process media.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process neural voice notes."""
    voice_file = await update.message.voice.get_file()
    path = os.path.join(config.VOICE_DIR, f"tg_voice_{uuid.uuid4().hex[:8]}.oga")
    await voice_file.download_to_drive(path)
    
    await update.message.chat.send_action(constants.ChatAction.TYPING)
    
    # Transcribe
    res = await voice_engine.transcribe(path)
    if res["status"] == "success":
        transcript = res["text"]
        await update.message.reply_text(f"🎤 *Transcribed:* _{transcript}_", parse_mode=constants.ParseMode.MARKDOWN)
        # Process the transcription as a message
        await handle_message(update, context, forced_message=transcript)
    else:
        logger.error(f"STT Error: {res}")
        await update.message.reply_text("⚠️ Auditory Interface Failure. I couldn't hear you clearly.")
    
    # Cleanup
    if os.path.exists(path): os.remove(path)

# ─── Chat Handler ────────────────────────────────────────────────

# ─── Neural Speed Utilities ────────────────────────────────────────

def fast_clean(text: str) -> str:
    """Zero-overhead response cleaning."""
    return text.strip().replace("\n\n", "\n")

async def send_typing_reply(update: Update, text: str):
    """Simulate human-like typing speed for the final response."""
    # Only use for short-ish responses to avoid annoying wait
    if len(text) < 500:
        # Send action
        await update.message.chat.send_action(constants.ChatAction.TYPING)
        delay = min(len(text) * 0.01, 3.0) 
        await asyncio.sleep(delay)
    
    # Send chunks if needed
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i : i + 4000])

def is_image_request(text: str) -> bool:
    """Hard override detection for visual art requests."""
    import re
    text = text.lower()
    patterns = [
        r"(create|make|generate|draw|show|design).*(image|car|logo|anime|art|picture|photo|poster|portrait)",
        r"(realistic|cyberpunk|anime|sketch|3d render).*(car|boy|girl|suit|city|building|nature|animal)",
        r"^draw ", r"^generate ", r"^create "
    ]
    return any(re.search(p, text) for p in patterns)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, forced_message: str = None):
    """Main message handler — features a Hard Override for image synthesis."""
    message = forced_message or update.message.text
    user_id = str(update.effective_user.id)
    conv_id = f"tg_{user_id}"

    # 🖼️ HARD OVERRIDE: Image Generation (Bypass Chat Engine)
    if is_image_request(message):
        await update.message.chat.send_action(constants.ChatAction.UPLOAD_PHOTO)
        from core.image_engine import ImageGenerator
        gen = ImageGenerator()
        
        # Clean prompt
        import re
        prompt = re.sub(r"(create|make|generate|draw|show|image|photo|picture|an|a )", "", message, flags=re.IGNORECASE).strip()
        
        # Generate 3 variations
        loop = asyncio.get_running_loop()
        for i in range(3):
            res = await loop.run_in_executor(
                None, lambda p=prompt, v=i: gen.generate(f"{p} variation {v+1}")
            )
            if res["status"] == "success":
                with open(res["path"], "rb") as photo:
                    await update.message.reply_photo(photo)
        
        return # 🚨 STOP: ZERO TEXT CHATTER

    # ⚡ INSTANT RESPONSE: acknowledgement
    status_msg = await update.message.reply_text("⚡ Processing...")

    # 🧠 TASTE DETECTION: Auto-learning interest patterns
    text_lower = message.lower()
    if "anime" in text_lower:
        update_user_taste(user_id, "anime")
    elif "kdrama" in text_lower or "k-drama" in text_lower:
        update_user_taste(user_id, "kdrama")
    elif "movie" in text_lower:
        update_user_taste(user_id, "movie")

    # 🧠 CACHE LOOKUP: Zero-lag retrieval
    cached = global_cache.get(message)
    if cached:
        await status_msg.edit_text(cached)
        return

    # Visual engagement: Typing indicator
    await update.message.chat.send_action(constants.ChatAction.TYPING)

    async with processing_semaphore:
        try:
            response_chunks = []
            class TelegramUser:
                def __init__(self, uid, prefs, tier, credits):
                    self.id = uid
                    self.username = f"tg_{uid}"
                    self.preferences = prefs
                    self.tier = tier
                    self.credits = credits

            def _generate():
                # Map context.user_data to preferences dict
                # Eagerly load all data inside the app context to avoid DetachedInstanceError
                with flask_app.app_context():
                    db_user = get_db_user(user_id)
                    user_prefs = db_user.preferences or {}
                    user_tier = db_user.tier
                    user_credits = db_user.credits
                    
                # Standard Mode User Parameters (Shared Brain ID)
                # The brain takes message, user_id, and conv_id
                response = brain.process(message, user_id=f"tg_{user_id}")
                response_chunks.append(response)
                
                # Update interests logic could go here if Brain returns it
                # For now we keep it simple as per Phase 4 prompt

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _generate)
            full_response = "".join(response_chunks).strip()

            # --- Midjourney-Level Media Delivery Hack ---
            # Parse for IMAGE_X: /path/to/image tags
            import re
            image_matches = re.findall(r"IMAGE_\d+:\s+(.*?)\s+\|\s+URL:", full_response)
            edit_match = re.search(r"SUCCESS: Image edited successfully\. File: .*?\. URL: .*", full_response)
            
            # If image paths found, send them first
            if image_matches:
                await update.message.chat.send_action(constants.ChatAction.UPLOAD_PHOTO)
                for path in image_matches:
                    if os.path.exists(path):
                        with open(path, "rb") as photo:
                            await update.message.reply_photo(photo)
                # Remove image paths from the final text response to keep it clean
                full_response = re.sub(r"IMAGE_\d+:.*?\n", "", full_response)
                full_response = full_response.replace("SUCCESS: HD Image variations generated.", "🎨 *HD Art Pack Synthesized:*")

            # Handle explicit edit success
            if "Image edited successfully" in full_response:
                 # Extract the filename to find the local path in IMAGE_GEN_DIR
                 filename_match = re.search(r"File:\s+(\S+)", full_response)
                 if filename_match:
                     fname = filename_match.group(1)
                     local_path = os.path.join(config.IMAGE_GEN_DIR, fname)
                     if os.path.exists(local_path):
                         with open(local_path, "rb") as photo:
                             await update.message.reply_photo(photo, caption="✨ *Modification Complete*")
                     full_response = "Image transformation successful. See above."

            if not full_response:
                full_response = "I processed your request but have no response. Perhaps my core model is idling?"

            # 1. Send Text Response with "Human Typing" feel
            final_cleaned = fast_clean(full_response)
            
            # 🧠 CACHE COMMIT: Save for future zero-lag requests
            global_cache.set(message, final_cleaned)
            
            # Use existing edit for speed
            await status_msg.edit_text(final_cleaned)

            # 2. Send Voice Response (if requested)
            if context.user_data.get("voice_mode", False):
                await update.message.chat.send_action(constants.ChatAction.RECORD_VOICE)
                # Remove markdown logic from text for cleaner speech
                clean_text = full_response.replace("*", "").replace("_", "").replace("`", "")
                # Limit text length for voice (optional, for performance)
                if len(clean_text) > 800: clean_text = clean_text[:800] + "..."
                
                voice_res = await voice_engine.speak(clean_text)
                if voice_res["status"] == "success":
                    voice_path = os.path.join(config.VOICE_DIR, voice_res["filename"])
                    with open(voice_path, "rb") as voice_file:
                        await update.message.reply_voice(voice_file)
                    # Cleanup
                    try: os.remove(voice_path)
                    except Exception: pass
                else:
                    logger.error(f"Voice Synthesis Error: voice_res={voice_res}")

            # 3. Handle Predictive Intelligence (Suggestions)
            last_user = context.user_data.pop("_last_user_obj", None)
            if last_user:
                # Check for general interest suggestions first
                suggestion = chat_engine.memory.predict_next(last_user.preferences)
                
                # Check for media-specific proactive suggestions
                taste_history = last_user.preferences.get("entertainment_taste", [])
                media_suggestion = recommender.get_proactive_suggestion(taste_history)
                
                final_suggestion = media_suggestion or (f"🔮 *You might also like:* `{suggestion}`" if suggestion else None)
                
                if final_suggestion:
                    # Only suggest if it's not already in the responses
                    if suggestion and suggestion.lower() in full_response.lower(): 
                       final_suggestion = media_suggestion # Fallback to media if general is redundant
                    
                    if final_suggestion:
                        await asyncio.sleep(1.5)
                        try:
                            # Sanitize markdown for suggestion
                            safe_suggestion = final_suggestion.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
                            await update.message.reply_text(final_suggestion, parse_mode=constants.ParseMode.MARKDOWN)
                        except Exception as sugg_err:
                            logger.warning(f"Proactive Suggestion failed to send: {sugg_err}")

        except Exception as e:
            logger.error(f"Chat failed for user {user_id}: {e}", exc_info=True)
            # Soft Fallback - try to answer even if main pipeline fails
            fallback_msg = "⚠️ *Intelligence Interface Flutter*\nMy complex reasoning core is recalibrating, but I'm still functional. How else can I assist you with simpler tasks?"
            await update.message.reply_text(fallback_msg, parse_mode=constants.ParseMode.MARKDOWN)

# ─── Scheduled Jobs ──────────────────────────────────────────────

async def daily_news_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Fetch and send top headlines to all subscribers."""
    logger.info("Starting scheduled daily news broadcast...")
    subs = get_subs()
    if not subs:
        return

    # Use agent to get news summary
    query = "latest top headlines in technology and world news"
    
    # Mock user for internal call
    class SystemUser:
        def __init__(self):
            self.id = "system"
            self.username = "system_scheduler"
            self.preferences = {}

    response_chunks = []
    def _generate():
        for chunk in chat_engine.chat_stream(query, SystemUser(), "daily_broadcast"):
            response_chunks.append(chunk)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _generate)
    news_report = "".join(response_chunks).strip()

    # Get Trending Media Picks for the day
    trending_kdrama = recommender.recommend("kdrama")[0]
    trending_anime = recommender.recommend("anime")[0]
    media_picks = f"🎬 *JARVIS TRENDING PICKS*\n• K-Drama: `{trending_kdrama}`\n• Anime: `{trending_anime}`"

    if news_report:
        formatted_report = f"📰 *DAILY INTELLIGENCE REPORT*\n\n{news_report}\n\n{media_picks}"
        for chat_id in subs:
            try:
                await context.bot.send_message(chat_id, formatted_report, parse_mode=constants.ParseMode.MARKDOWN)
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")

async def audit_missions(context: ContextTypes.DEFAULT_TYPE):
    """
    Background Task: Scan for pending missions and send proactive nudges to subscribers.
    """
    logger.info("Executing Proactive Mission Audit...")
    from models import Mission, User
    
    subs = get_subs()
    if not subs: return

    with flask_app.app_context():
        # Find pending missions (highest priority first)
        pending = Mission.query.filter_by(status='pending').order_by(Mission.priority.desc()).all()
        
        if not pending:
            logger.info("Audit Complete: No pending missions found.")
            return

        # Personalize nudge for each subscriber
        for chat_id in subs:
            try:
                # Group missions by priority
                high = [m for m in pending if m.priority == 3]
                count = len(pending)
                
                if high:
                    mission = high[0]
                    msg = (
                        f"🏹 *Stark Intelligence Briefing*\n\n"
                        f"Sir, I've noted `{count}` incomplete missions on your grid.\n"
                        f"Most critical: *{mission.title}*\n\n"
                        f"Should I initialize a research node or coordinate the next steps?"
                    )
                else:
                    msg = f"🛰️ *Mission Monitor*: You have `{count}` pending tasks. Would you like a summary of the agenda?"

                await context.bot.send_message(chat_id, msg, parse_mode=constants.ParseMode.MARKDOWN)
            except Exception as e:
                logger.warning(f"Failed to nudge {chat_id}: {e}")

# ─── Main ────────────────────────────────────────────────────────

def main():
    """Start the Pro Telegram Bot."""
    if not TELEGRAM_AVAILABLE:
        logging.error("Telegram Node Startup Failed: 'python-telegram-bot' module is missing. Node will remain offline.")
        return

    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN missing in configuration.")
        return

    init_jarvis()

    # Build app with JobQueue
    app = Application.builder().token(token).build()

    # Setup Schedule (Only if JobQueue is available)
    if app.job_queue:
        # 1. Daily News (9:00 AM)
        app.job_queue.run_daily(daily_news_broadcast, time=time(hour=9, minute=0))
        
        # 2. Mission Auditor (Every 4 hours)
        app.job_queue.run_repeating(audit_missions, interval=14400, first=300)
    else:
        logger.warning("Telegram JobQueue Offline: 'apscheduler' not found. Scheduled broadcasts disabled.")

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("voice", voice_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("open", open_app_command))
    app.add_handler(CommandHandler("nudge", nudge_command))
    app.add_handler(CommandHandler("ig_analytics", ig_analytics_command))
    app.add_handler(CommandHandler("ig_ideas", ig_ideas_command))
    app.add_handler(CommandHandler("ig_caption", ig_caption_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("=" * 60)
    logger.info("  JARVIS PROFESSIONAL — TELEGRAM NODE ACTIVE")
    logger.info("=" * 60)

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()



















