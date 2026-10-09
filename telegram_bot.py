"""
Jarvis Telegram Bot — Professional Edition
==========================================

Production-focused Telegram node for the Jarvis assistant.

Major hardening:
- User-scoped caching (prevents cross-user response leakage)
- Per-user rate limiting
- Secure admin-only OS application launcher with allowlist
- No hard-coded default admin password
- Atomic subscription persistence
- Timezone-aware scheduled jobs
- Safer Markdown/HTML delivery with plain-text fallback
- Better media cleanup and error isolation
- Safer image prompt parsing
- More defensive recommender/scheduler handling
- Graceful logging and configuration validation
- Compatibility with python-telegram-bot v20+
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import random
import re
import sys
import tempfile
import time as monotonic_time
import uuid
from collections import defaultdict, deque
from datetime import time as dt_time
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Keep local project imports working when this file is launched directly.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask

try:
    from telegram import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        Update,
        constants,
    )
    from telegram.error import Conflict, NetworkError, TelegramError
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.error(
        "Telegram Node Offline: 'python-telegram-bot' is not installed. "
        "Install it with: pip install python-telegram-bot[job-queue]"
    )

    class Update:  # type: ignore[no-redef]
        ALL_TYPES = []

    class InlineKeyboardButton:  # type: ignore[no-redef]
        def __init__(self, text: str, callback_data: Optional[str] = None):
            self.text = text
            self.callback_data = callback_data

    class InlineKeyboardMarkup:  # type: ignore[no-redef]
        def __init__(self, inline_keyboard: list[list[Any]]):
            self.inline_keyboard = inline_keyboard

    class ContextTypes:  # type: ignore[no-redef]
        class DEFAULT_TYPE:  # type: ignore[no-redef]
            pass

    class CallbackQueryHandler:  # type: ignore[no-redef]
        def __init__(self, callback: Any, pattern: Any = None):
            pass

    class constants:  # type: ignore[no-redef]
        class ParseMode:
            MARKDOWN = "Markdown"
            HTML = "HTML"

        class ChatAction:
            TYPING = "typing"
            UPLOAD_PHOTO = "upload_photo"
            RECORD_VOICE = "record_voice"

    class filters:  # type: ignore[no-redef]
        TEXT = COMMAND = PHOTO = VOICE = None

    class Conflict(Exception):
        pass

    class NetworkError(Exception):
        pass

    class TelegramError(Exception):
        pass

import config
from core.agent_engine import AgentEngine
from core.brain import JarvisBrain
from core.cache import global_cache
from core.chat_engine import ChatEngine
from core.instagram_engine import InstagramEngine
from core.knowledge_manager import KnowledgeManager
from core.model_manager import ModelManager
from core.recommender import EntertainmentRecommender
from core.voice_engine import VoiceEngine


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path(getattr(config, "LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Ensure sys.stdout handles UTF-8 correctly on Windows
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=getattr(logging, str(os.getenv("JARVIS_LOG_LEVEL", "INFO")).upper(), logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "telegram_bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("jarvis.pro")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(getattr(config, "DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SUBS_FILE = DATA_DIR / "subscriptions.json"
MODES_FILE = DATA_DIR / "user_modes.json"

# Prefer an explicit application timezone. Defaulting to Asia/Kolkata is
# intentional for the current deployment, but can be changed with env/config.
TIMEZONE_NAME = (
    os.getenv("JARVIS_TIMEZONE")
    or getattr(config, "TIMEZONE", None)
    or "Asia/Kolkata"
)
try:
    BOT_TZ = ZoneInfo(TIMEZONE_NAME)
except ZoneInfoNotFoundError:
    logger.warning("Invalid timezone %r; falling back to UTC.", TIMEZONE_NAME)
    BOT_TZ = ZoneInfo("UTC")

# Concurrency and rate limits can be tuned without editing code.
MAX_CONCURRENT_REQUESTS = max(
    1, int(os.getenv("JARVIS_MAX_CONCURRENT_REQUESTS", "10"))
)
RATE_LIMIT_WINDOW = max(10, int(os.getenv("JARVIS_RATE_LIMIT_WINDOW", "60")))
RATE_LIMIT_MAX_REQUESTS = max(1, int(os.getenv("JARVIS_RATE_LIMIT_MAX", "30")))
MAX_MESSAGE_LENGTH = max(1000, int(os.getenv("JARVIS_MAX_MESSAGE_LENGTH", "12000")))

# Cache is disabled by default because Jarvis responses can be personalized.
CACHE_ENABLED = os.getenv("JARVIS_CACHE_ENABLED", "false").lower() in {
    "1", "true", "yes", "on"
}

# Only explicitly approved administrators can invoke OS-level commands.
# Never grant /open to everyone just because they can access the bot.
def _parse_int_set(raw: Any) -> set[int]:
    values: set[int] = set()
    if raw is None:
        return values
    if isinstance(raw, (list, tuple, set)):
        iterable = raw
    else:
        iterable = re.split(r"[,\s]+", str(raw))
    for item in iterable:
        try:
            if str(item).strip():
                values.add(int(item))
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid admin Telegram ID: %r", item)
    return values


ADMIN_IDS = _parse_int_set(
    os.getenv("JARVIS_ADMIN_TELEGRAM_IDS")
    or getattr(config, "ADMIN_TELEGRAM_IDS", None)
)

# App launcher allowlist. Keys are user-facing aliases; values are passed to
# the existing OS engine. No arbitrary shell command is accepted.
DEFAULT_APP_ALLOWLIST = {
    "chrome",
    "google chrome",
    "firefox",
    "edge",
    "notepad",
    "calculator",
    "calc",
    "code",
    "vscode",
}
APP_ALLOWLIST = {
    item.strip().lower()
    for item in (
        os.getenv("JARVIS_APP_ALLOWLIST")
        or getattr(config, "APP_ALLOWLIST", None)
        or ",".join(sorted(DEFAULT_APP_ALLOWLIST))
    ).split(",")
    if item.strip()
}


# ---------------------------------------------------------------------------
# Global engine state
# ---------------------------------------------------------------------------

model_manager: Optional[ModelManager] = None
knowledge_manager: Optional[KnowledgeManager] = None
chat_engine: Optional[ChatEngine] = None
agent_engine: Optional[AgentEngine] = None
brain: Optional[JarvisBrain] = None
flask_app: Optional[Flask] = None
voice_engine: Optional[VoiceEngine] = None
recommender: Optional[EntertainmentRecommender] = None
instagram_engine: Optional[InstagramEngine] = None

processing_semaphore: Optional[asyncio.Semaphore] = None
_rate_buckets: dict[int, deque[float]] = defaultdict(deque)
_rate_lock: Optional[asyncio.Lock] = None


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_jarvis() -> None:
    """Initialize the Jarvis engine stack and database."""
    global model_manager, knowledge_manager, chat_engine, agent_engine
    global brain, flask_app, voice_engine, recommender, instagram_engine

    logger.info("Initializing Jarvis Pro Engine...")

    model_manager = ModelManager()
    knowledge_manager = KnowledgeManager()
    chat_engine = ChatEngine(model_manager, knowledge_manager)
    agent_engine = AgentEngine()
    brain = JarvisBrain(agent_engine)
    voice_engine = VoiceEngine()
    recommender = EntertainmentRecommender()
    instagram_engine = InstagramEngine()

    flask_app = Flask(__name__)
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    from models import db, User

    db.init_app(flask_app)

    with flask_app.app_context():
        db.create_all()

        # Security fix: the old implementation silently created Admin/admin.
        # That is unacceptable in production. Bootstrap only when a password
        # is explicitly provided by configuration.
        if not User.query.filter_by(username="Admin").first():
            bootstrap_password = (
                os.getenv("JARVIS_BOOTSTRAP_ADMIN_PASSWORD")
                or getattr(config, "ADMIN_PASSWORD", None)
            )
            if bootstrap_password:
                admin = User(username="Admin", email="admin@local.host")
                admin.set_password(bootstrap_password)
                db.session.add(admin)
                db.session.commit()
                logger.warning(
                    "Bootstrap Admin account created. Rotate the bootstrap "
                    "password after first login."
                )
            else:
                logger.warning(
                    "No Admin account exists and no bootstrap password is configured. "
                    "Skipping automatic admin creation."
                )

    _ensure_subscription_file()
    logger.info(
        "Jarvis Pro Engine — ONLINE | timezone=%s | cache=%s | admins=%d",
        BOT_TZ.key,
        CACHE_ENABLED,
        len(ADMIN_IDS),
    )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _ensure_subscription_file() -> None:
    if not SUBS_FILE.exists():
        _atomic_write_json(SUBS_FILE, {"subscribers": []})


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except OSError:
            pass


_subs_lock = None


def get_subs() -> set[int]:
    """Load subscriber IDs defensively."""
    try:
        with SUBS_FILE.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return {int(x) for x in raw.get("subscribers", [])}
    except (OSError, ValueError, TypeError) as exc:
        logger.error("Could not read subscriptions: %s", exc)
        return set()


def save_subs(subs: set[int]) -> None:
    """Atomically persist subscribers."""
    _atomic_write_json(SUBS_FILE, {"subscribers": sorted(subs)})


# ---------------------------------------------------------------------------
# Professional Operating Modes
# ---------------------------------------------------------------------------

OPERATING_MODES: dict[str, dict[str, Any]] = {
    "ai": {
        "id": "ai",
        "name": "AI Mode",
        "icon": "🧠",
        "label": "🧠 AI Mode",
        "command": "/ai",
        "summary": "General-purpose autonomous assistant; chooses the best capability automatically",
        "prompt": (
            "You are JARVIS operating in [🧠 AI Mode - Autonomous Router Protocol].\n"
            "You possess full autonomous command across all Jarvis subsystems: Security Analysis, "
            "Code Engineering, Deep Research, Creative Generation, and Neural Chat.\n"
            "CRITICAL PROTOCOL: For multi-faceted requests (such as security auditing + code fixing + explanation), "
            "you autonomously orchestrate and route the solution through the required specialized pipelines without "
            "requiring the user to switch modes manually:\n"
            "1. Security / Audit Phase (Security Scan) -> Identify risks, vulnerabilities, CVEs, or flaws.\n"
            "2. Engineering / Remediation Phase (Code Forge) -> Generate complete, verified, and hardened code fixes.\n"
            "3. Executive Synthesis & Explanation Phase (Neural Chat) -> Provide an articulate, high-signal explanation of changes.\n"
            "Deliver comprehensive, production-grade results."
        ),
    },
    "chat": {
        "id": "chat",
        "name": "Neural Chat",
        "icon": "💬",
        "label": "💬 Neural Chat",
        "command": "/chat",
        "summary": "Fast conversational mode with memory and personality",
        "prompt": (
            "You are JARVIS operating in [💬 Neural Chat Mode].\n"
            "Tone: The authentic, loyal, sharp-witted British peer to Ayush Stark.\n"
            "Focus: Fast conversational cadence, deep memory recall, emotional intelligence, and witty banter.\n"
            "Rules:\n"
            "- Keep responses conversational, articulate, and direct.\n"
            "- Avoid robotic disclaimers or repetitive preambles.\n"
            "- Act as an intellectual companion, advisor, and strategist."
        ),
    },
    "code": {
        "id": "code",
        "name": "Code Forge",
        "icon": "⚙️",
        "label": "⚙️ Code Forge",
        "command": "/code",
        "summary": "Coding, debugging, refactoring, architecture, tests",
        "prompt": (
            "You are JARVIS operating in [⚙️ Code Forge - Elite Software Engineering Node].\n"
            "Role: Elite software architect, systems engineer, and principal programmer.\n"
            "Rules:\n"
            "- Produce production-ready, clean, well-tested, and secure code.\n"
            "- When fixing bugs or refactoring, provide complete code blocks with precise explanation of root causes.\n"
            "- Include type hints, comprehensive error handling, and performance considerations.\n"
            "- Highlight architectural decisions and trade-offs where relevant."
        ),
    },
    "creative": {
        "id": "creative",
        "name": "Creative Core",
        "icon": "🎨",
        "label": "🎨 Creative Core",
        "command": "/creative",
        "summary": "Images, writing, ideas, captions, scripts, creative generation",
        "prompt": (
            "You are JARVIS operating in [🎨 Creative Core - Generative & Aesthetic Foundry].\n"
            "Role: Master creative director, storyteller, copywriter, and visual ideator.\n"
            "Rules:\n"
            "- Generate imaginative narratives, high-impact scripts, engaging social copy, and creative concepts.\n"
            "- When designing image or video prompts, craft vivid, cinematic descriptive prompts featuring lighting, camera lens, atmospheric details, and composition.\n"
            "- Write with compelling style, rhythm, and flair tailored to the user's vision."
        ),
    },
    "security": {
        "id": "security",
        "name": "Security Scan",
        "icon": "🛡️",
        "label": "🛡️ Security Scan",
        "command": "/security",
        "summary": "Security auditing, vulnerability detection, configuration review, defensive hardening",
        "prompt": (
            "You are JARVIS operating in [🛡️ Security Scan - Defensive Cyber Intelligence & Audit Mode].\n"
            "Role: Principal cybersecurity researcher, application security auditor, and defensive hardening specialist.\n"
            "Rules:\n"
            "- Rigorously evaluate code, configs, architectures, and inputs for vulnerabilities (OWASP Top 10, CWE, secret leaks, auth bypasses, injection, RCE, insecure dependencies).\n"
            "- Structure security reports with:\n"
            "  1. 🔴 Threat / Vulnerability Summary (Severity: CRITICAL / HIGH / MEDIUM / LOW)\n"
            "  2. 🔍 Attack Vector & Impact Analysis\n"
            "  3. 🛡️ Concrete Remediation & Hardened Code Implementation\n"
            "  4. 📋 Defensive Recommendations & Security Hardening Checklist."
        ),
    },
    "research": {
        "id": "research",
        "name": "Intel Research",
        "icon": "🔎",
        "label": "🔎 Intel Research",
        "command": "/research",
        "summary": "Web research, source comparison, current information, structured intelligence reports",
        "prompt": (
            "You are JARVIS operating in [🔎 Intel Research - Strategic Intelligence & Deep Investigation Node].\n"
            "Role: Senior intelligence analyst and research strategist.\n"
            "Rules:\n"
            "- Formulate structured intelligence briefings using real-time information, data comparison, and cross-source validation.\n"
            "- Structure briefings with:\n"
            "  * 📌 Executive Summary\n"
            "  * 📊 Key Findings & Evidence\n"
            "  * ⚖️ Comparative Analysis (contrasting perspectives / sources)\n"
            "  * 🧭 Strategic Implications & Actionable Takeaways\n"
            "- Maintain rigorous objectivity, highlight uncertainties, and cite specific data."
        ),
    },
}

_modes_lock = None


def get_user_mode(user_id: int | str) -> str:
    """Return the user's persistent operating mode, defaulting to 'ai'."""
    uid = str(user_id)
    try:
        if MODES_FILE.exists():
            with MODES_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                mode = data.get(uid)
                if mode in OPERATING_MODES:
                    return mode
    except Exception as exc:
        logger.debug("Failed reading user mode for %s: %s", uid, exc)
    return "ai"


def save_user_mode(user_id: int | str, mode: str) -> None:
    """Atomically persist user operating mode."""
    if mode not in OPERATING_MODES:
        return
    uid = str(user_id)
    data: dict[str, str] = {}
    try:
        if MODES_FILE.exists():
            with MODES_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
    except Exception:
        data = {}
    data[uid] = mode
    _atomic_write_json(MODES_FILE, data)


def build_mode_menu(current_mode: str) -> tuple[str, InlineKeyboardMarkup]:
    """Render the Telegram operating modes interactive menu."""
    active_info = OPERATING_MODES.get(current_mode, OPERATING_MODES["ai"])
    text = (
        "🤖 *JARVIS OPERATING MODES*\n\n"
        "🧠 AI Mode\n"
        "💬 Neural Chat\n"
        "⚙️ Code Forge\n"
        "🎨 Creative Core\n"
        "🛡️ Security Scan\n"
        "🔎 Intel Research\n\n"
        f"Current: {active_info['label']}\n\n"
        "Select an operating mode:"
    )

    def _btn_label(mode_key: str) -> str:
        info = OPERATING_MODES[mode_key]
        if mode_key == current_mode:
            return f"{info['label']} ✅"
        return info["label"]

    keyboard = [
        [
            InlineKeyboardButton(_btn_label("ai"), callback_data="mode:ai"),
            InlineKeyboardButton(_btn_label("chat"), callback_data="mode:chat"),
        ],
        [
            InlineKeyboardButton(_btn_label("code"), callback_data="mode:code"),
            InlineKeyboardButton(_btn_label("creative"), callback_data="mode:creative"),
        ],
        [
            InlineKeyboardButton(_btn_label("security"), callback_data="mode:security"),
            InlineKeyboardButton(_btn_label("research"), callback_data="mode:research"),
        ],
    ]
    return text, InlineKeyboardMarkup(keyboard)


def analyze_autonomous_pipeline(message: str) -> list[str]:
    """
    Detect multi-domain operations for AI Mode.
    Returns ordered list of required mode phases, e.g. ['security', 'code', 'chat'].
    """
    msg = message.lower()

    has_security = any(
        w in msg
        for w in [
            "vulnerabilit", "security", "audit", "exploit", "cve", "sanitize",
            "injection", "leak", "secret", "owasp", "threat", "insecure", "malicious",
        ]
    )
    has_code = any(
        w in msg
        for w in [
            "fix the bug", "fix bugs", "fix bug", "fix the bugs", "fix", "code",
            "refactor", "patch", "implement", "function", "script", "program",
            "python", "javascript", "test", "compile", "error", "rewrite", "syntax",
            "debug",
        ]
    )
    has_explain = any(
        w in msg
        for w in [
            "explain", "summary", "summarize", "walkthrough", "break down",
            "breakdown", "why", "changes", "describe what you did", "explanation",
        ]
    )
    has_research = any(
        w in msg
        for w in [
            "research", "search the web", "look up", "find latest", "compare",
            "market intel", "investigate", "recent news",
        ]
    )
    has_creative = any(
        w in msg
        for w in [
            "write a story", "creative", "caption", "poem", "generate image",
            "script for", "marketing", "slogan",
        ]
    )

    # Multi-phase combinations
    if has_security and has_code:
        phases = ["security", "code"]
        if has_explain:
            phases.append("chat")
        return phases

    if has_research and has_code:
        phases = ["research", "code"]
        if has_explain:
            phases.append("chat")
        return phases

    if has_research and has_creative:
        return ["research", "creative"]

    return []


def get_db_user_data(telegram_id: str) -> dict[str, Any]:
    """
    Read only primitive values while inside the SQLAlchemy app context.

    This avoids leaking detached ORM objects into asynchronous code.
    """
    if flask_app is None:
        raise RuntimeError("Jarvis database is not initialized.")

    from models import User

    username = f"tg_{telegram_id}"
    with flask_app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            from models import db

            user = User(
                username=username,
                email=f"{username}@telegram.local",
            )
            user.set_password(str(telegram_id))
            db.session.add(user)
            db.session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "preferences": dict(user.preferences or {}),
            "tier": user.tier,
            "credits": user.credits,
        }


def update_user_taste(telegram_id: str, category: str) -> None:
    """Persist entertainment preferences, capped to the last 20 entries."""
    if flask_app is None:
        return

    from models import db, User

    username = f"tg_{telegram_id}"
    try:
        with flask_app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                return

            prefs = dict(user.preferences or {})
            history = list(prefs.get("entertainment_taste", []))
            history.append(category.lower().strip())
            prefs["entertainment_taste"] = history[-20:]
            user.preferences = prefs
            db.session.commit()
    except Exception:
        logger.exception("Failed to update entertainment taste for %s", telegram_id)


# ---------------------------------------------------------------------------
# Security / request controls
# ---------------------------------------------------------------------------

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_rate_limit(user_id: int) -> bool:
    """
    Return True when the request is allowed.

    A small in-memory limiter protects the local process from accidental
    floods. Production deployments with multiple replicas should move this
    state to Redis or another shared store.
    """
    global _rate_lock

    if _rate_lock is None:
        _rate_lock = asyncio.Lock()

    now = monotonic_time.monotonic()
    async with _rate_lock:
        bucket = _rate_buckets[user_id]
        cutoff = now - RATE_LIMIT_WINDOW
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            return False

        bucket.append(now)
        return True


def normalize_user_text(text: str) -> str:
    text = (text or "").strip()
    if len(text) > MAX_MESSAGE_LENGTH:
        return text[:MAX_MESSAGE_LENGTH]
    return text


# ---------------------------------------------------------------------------
# Telegram output helpers
# ---------------------------------------------------------------------------

def plain_text(text: str) -> str:
    """Remove common Markdown syntax before voice/TTS delivery."""
    text = re.sub(r"[*_`~]", "", text or "")
    return text.strip()


async def safe_reply(
    update: Update,
    text: str,
    *,
    parse_mode: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Send a message without allowing malformed model-generated Markdown/HTML
    to break the whole handler.
    """
    text = text or "I completed the operation but returned no text."
    try:
        return await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            **kwargs,
        )
    except TelegramError:
        logger.warning("Formatted Telegram message failed; retrying as plain text.")
        return await update.message.reply_text(
            re.sub(r"[*_`]", "", text),
            **kwargs,
        )


async def edit_status(status_msg: Any, text: str) -> None:
    try:
        await status_msg.edit_text(text, parse_mode=constants.ParseMode.MARKDOWN)
    except TelegramError:
        try:
            await status_msg.edit_text(text)
        except TelegramError:
            try:
                await status_msg.edit_text(re.sub(r"[*_`]", "", text))
            except TelegramError:
                logger.debug("Unable to edit Telegram status message.", exc_info=True)


async def send_chunked(
    update: Update,
    text: str,
    *,
    parse_mode: Optional[str] = None,
) -> None:
    """Telegram has a message size limit; split large model outputs safely."""
    text = text or ""
    if not text:
        return

    for start in range(0, len(text), 3900):
        chunk = text[start:start + 3900]
        await safe_reply(update, chunk, parse_mode=parse_mode)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = context.user_data.get("operating_mode") or get_user_mode(user_id)
    mode_label = OPERATING_MODES.get(current_mode, OPERATING_MODES["ai"])["label"]

    welcome_text = (
        "🤖 *Jarvis Pro Online*\n\n"
        f"Your personal AI assistant is online. Active Mode: *{mode_label}*\n\n"
        "*Operating Modes*\n"
        "🧠 `/ai <request>` — Autonomous Router\n"
        "💬 `/chat <request>` — Neural Chat (memory & personality)\n"
        "⚙️ `/code <request>` — Code Forge (engineering & tests)\n"
        "🎨 `/creative <request>` — Creative Core (writing & visual prompts)\n"
        "🛡️ `/security <request>` — Security Scan (vulnerabilities & hardening)\n"
        "🔎 `/research <request>` — Intel Research (web intel & reports)\n"
        "🎛️ `/mode` — Interactive Mode Selector\n\n"
        "*Core Commands*\n"
        "💬 Normal chat — send any message\n"
        "🖼️ `/image <prompt>` — generate art\n"
        "🎬 `/video <prompt>` — request AI video generation\n"
        "🔍 `/search <query>` — web search\n"
        "📰 `/news <topic>` — latest news\n"
        "📅 `/subscribe` — daily intelligence briefing\n"
        "🔕 `/unsubscribe` — stop daily briefings\n"
        "🔄 `/new` — reset current conversation memory\n"
        "🎙️ `/voice on|off` — voice replies\n"
        "📊 `/status` — system diagnostics\n"
        "🛠️ `/skills` — list registered skills\n"
        "⚡ `/run_skill <id>` — execute a skill\n"
        "🎯 `/nudge` — mission audit\n\n"
        "Send a photo with a caption to analyze or edit it."
    )
    await safe_reply(update, welcome_text, parse_mode=constants.ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = context.user_data.get("operating_mode") or get_user_mode(user_id)
    mode_label = OPERATING_MODES.get(current_mode, OPERATING_MODES["ai"])["label"]

    help_text = (
        "🚀 *Jarvis Professional Help*\n\n"
        f"Currently running in *{mode_label}*.\n\n"
        "*Six Operating Modes*\n"
        "• `/mode` — Open interactive selector menu\n"
        "• `/ai <request>` — General autonomous routing across all domains\n"
        "• `/chat <request>` — Fast conversational mode with memory\n"
        "• `/code <request>` — Production code, bug fixes & architecture\n"
        "• `/creative <request>` — Writing, scripts, captions & art prompts\n"
        "• `/security <request>` — Vulnerability audits & defensive hardening\n"
        "• `/research <request>` — Real-time web intel & structured reports\n\n"
        "*Autonomous Routing in AI Mode*\n"
        "AI Mode detects multi-discipline tasks (e.g., _\"Check this Python project for vulnerabilities, fix the bugs, then explain the changes\"_) and automatically routes through *Security Scan ➔ Code Forge ➔ Neural Chat* without requiring manual mode switches.\n\n"
        "*Other Capabilities*\n"
        "• `/image <prompt>` / `/video <prompt>`\n"
        "• `/search <query>` / `/news <topic>`\n"
        "• `/voice on|off` / `/status` / `/new`\n\n"
        "OS application launching (`/open <app>`) is restricted to configured administrators."
    )
    await safe_reply(update, help_text, parse_mode=constants.ParseMode.MARKDOWN)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = normalize_user_text(" ".join(context.args))
    if not query:
        await safe_reply(
            update,
            "🔍 Usage: `/search latest space launch`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    await safe_reply(update, f"🔎 Searching for: {query}...")
    await handle_message(update, context, forced_message=f"search {query}")


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = normalize_user_text(" ".join(context.args))
    if not prompt:
        await safe_reply(
            update,
            "🖼️ Usage: `/image a futuristic city`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    await safe_reply(update, "🎨 Synthesizing image...")
    await handle_message(update, context, forced_message=f"generate image {prompt}")


async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = normalize_user_text(" ".join(context.args))
    if not prompt:
        await safe_reply(
            update,
            "🎬 Usage: `/video iron man flying`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    await safe_reply(update, "🎬 Initializing Video Node...")
    await handle_message(update, context, forced_message=f"create video {prompt}")


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = normalize_user_text(" ".join(context.args)) or "general"
    await safe_reply(update, f"📰 Fetching updates on: {topic}...")
    await handle_message(
        update,
        context,
        forced_message=f"latest news about {topic}",
    )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _subs_lock
    if _subs_lock is None:
        _subs_lock = asyncio.Lock()

    chat_id = update.effective_chat.id
    async with _subs_lock:
        subs = get_subs()
        if chat_id in subs:
            await safe_reply(update, "✅ You are already subscribed.")
            return

        subs.add(chat_id)
        save_subs(subs)

    await safe_reply(
        update,
        f"🔔 Subscribed. Daily intelligence will be sent at 09:00 {BOT_TZ.key}.",
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _subs_lock
    if _subs_lock is None:
        _subs_lock = asyncio.Lock()

    chat_id = update.effective_chat.id
    async with _subs_lock:
        subs = get_subs()
        if chat_id not in subs:
            await safe_reply(update, "You are not currently subscribed.")
            return

        subs.remove(chat_id)
        save_subs(subs)

    await safe_reply(update, "🔕 Unsubscribed from daily intelligence.")


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = bool(context.user_data.get("voice_mode", False))
        await safe_reply(
            update,
            f"🎙️ Voice Mode: {'ON' if current else 'OFF'}\n"
            "Use `/voice on` or `/voice off`.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    mode = context.args[0].lower()
    if mode == "on":
        context.user_data["voice_mode"] = True
        await safe_reply(update, "🔊 Voice Mode Enabled.")
    elif mode == "off":
        context.user_data["voice_mode"] = False
        await safe_reply(update, "🔈 Voice Mode Disabled.")
    else:
        await safe_reply(update, "Usage: `/voice on` or `/voice off`.")


async def nudge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_reply(update, "🎯 Scanning Mission Grid...")
    await audit_missions(context)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Render or switch the Jarvis operating mode.
    If called without args: presents an interactive inline menu.
    If called with an arg: persists the specified mode.
    """
    user_id = update.effective_user.id
    if not context.args:
        current_mode = context.user_data.get("operating_mode") or get_user_mode(user_id)
        text, reply_markup = build_mode_menu(current_mode)
        await safe_reply(
            update,
            text,
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
        return

    requested = " ".join(context.args).strip().lower()
    alias_map = {
        "ai": "ai",
        "ai mode": "ai",
        "autonomous": "ai",
        "chat": "chat",
        "neural chat": "chat",
        "neural": "chat",
        "code": "code",
        "code forge": "code",
        "forge": "code",
        "coding": "code",
        "creative": "creative",
        "creative core": "creative",
        "security": "security",
        "security scan": "security",
        "sec": "security",
        "research": "research",
        "intel research": "research",
        "intel": "research",
    }
    mode_key = alias_map.get(requested)
    if not mode_key:
        for k, v in OPERATING_MODES.items():
            if requested in v["name"].lower():
                mode_key = k
                break

    if mode_key and mode_key in OPERATING_MODES:
        context.user_data["operating_mode"] = mode_key
        save_user_mode(user_id, mode_key)
        info = OPERATING_MODES[mode_key]
        await safe_reply(
            update,
            f"✅ Operating mode set to *{info['label']}*.\n_{info['summary']}_",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
    else:
        modes = getattr(config, "PERSONALITY_PROMPTS", {})
        if requested in modes:
            context.user_data["personality"] = requested
            await safe_reply(
                update,
                f"🔥 Personality synced: `{requested}`.",
                parse_mode=constants.ParseMode.MARKDOWN,
            )
        else:
            options = ", ".join(f"`{k}`" for k in OPERATING_MODES.keys())
            await safe_reply(
                update,
                f"❌ Unknown mode `{requested}`.\nAvailable modes: {options}\n\nUse `/mode` to open the interactive menu.",
                parse_mode=constants.ParseMode.MARKDOWN,
            )


async def mode_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive inline keyboard taps for operating mode selection."""
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    if not data.startswith("mode:"):
        return

    selected_mode = data.split(":", 1)[1].strip()
    if selected_mode not in OPERATING_MODES:
        await query.answer("Unknown mode selection.")
        return

    user_id = update.effective_user.id
    context.user_data["operating_mode"] = selected_mode
    save_user_mode(user_id, selected_mode)

    mode_info = OPERATING_MODES[selected_mode]
    await query.answer(f"Switched to {mode_info['label']}", show_alert=False)

    text, reply_markup = build_mode_menu(selected_mode)
    try:
        await query.edit_message_text(
            text=text,
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
    except TelegramError:
        pass


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute request in AI Mode or switch persistent mode to AI Mode."""
    request = normalize_user_text(" ".join(context.args))
    if not request:
        user_id = update.effective_user.id
        context.user_data["operating_mode"] = "ai"
        save_user_mode(user_id, "ai")
        await safe_reply(
            update,
            "🧠 Operating mode set to *AI Mode*.\n"
            "_Autonomous router active. Tasks spanning security, code, and explanations will be coordinated automatically._\n\n"
            "Usage: `/ai <request>` for single-turn execution, or send any normal message.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await handle_message(update, context, forced_message=request, execution_mode="ai")


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute request in Neural Chat mode or switch persistent mode to Neural Chat."""
    request = normalize_user_text(" ".join(context.args))
    if not request:
        user_id = update.effective_user.id
        context.user_data["operating_mode"] = "chat"
        save_user_mode(user_id, "chat")
        await safe_reply(
            update,
            "💬 Operating mode set to *Neural Chat*.\n"
            "_Fast conversational mode with memory and authentic Jarvis personality active._\n\n"
            "Usage: `/chat <request>` or send any message.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await handle_message(update, context, forced_message=request, execution_mode="chat")


async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute request in Code Forge mode or switch persistent mode to Code Forge."""
    request = normalize_user_text(" ".join(context.args))
    if not request:
        user_id = update.effective_user.id
        context.user_data["operating_mode"] = "code"
        save_user_mode(user_id, "code")
        await safe_reply(
            update,
            "⚙️ Operating mode set to *Code Forge*.\n"
            "_Software engineering, syntax perfection, architecture, refactoring, and tests active._\n\n"
            "Usage: `/code <request>` or send any coding prompt.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await handle_message(update, context, forced_message=request, execution_mode="code")


async def creative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute request in Creative Core mode or switch persistent mode to Creative Core."""
    request = normalize_user_text(" ".join(context.args))
    if not request:
        user_id = update.effective_user.id
        context.user_data["operating_mode"] = "creative"
        save_user_mode(user_id, "creative")
        await safe_reply(
            update,
            "🎨 Operating mode set to *Creative Core*.\n"
            "_Generative writing, aesthetic innovation, captions, scripts, and art concepts active._\n\n"
            "Usage: `/creative <request>` or send any creative request.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await handle_message(update, context, forced_message=request, execution_mode="creative")


async def security_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute request in Security Scan mode or switch persistent mode to Security Scan."""
    request = normalize_user_text(" ".join(context.args))
    if not request:
        user_id = update.effective_user.id
        context.user_data["operating_mode"] = "security"
        save_user_mode(user_id, "security")
        await safe_reply(
            update,
            "🛡️ Operating mode set to *Security Scan*.\n"
            "_Vulnerability detection, configuration review, and defensive hardening active._\n\n"
            "Usage: `/security <request>` or send any security audit request.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await handle_message(update, context, forced_message=request, execution_mode="security")


async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute request in Intel Research mode or switch persistent mode to Intel Research."""
    request = normalize_user_text(" ".join(context.args))
    if not request:
        user_id = update.effective_user.id
        context.user_data["operating_mode"] = "research"
        save_user_mode(user_id, "research")
        await safe_reply(
            update,
            "🔎 Operating mode set to *Intel Research*.\n"
            "_Web research, verified facts, source comparison, and structured intelligence reports active._\n\n"
            "Usage: `/research <request>` or send any intelligence research prompt.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await handle_message(update, context, forced_message=request, execution_mode="research")


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if chat_engine is None:
        await safe_reply(update, "⚠️ Chat engine is not initialized.")
        return

    user_id = str(update.effective_user.id)
    chat_engine.new_conversation(
        conv_id=f"tg_{user_id}",
        title=f"Telegram-{user_id}",
    )
    if brain and hasattr(brain, "history"):
        brain.history[f"tg_{user_id}"] = []
    await safe_reply(update, "🔄 Conversation memory reset. Fresh mental state ready.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if model_manager is None:
        await safe_reply(update, "⚠️ Jarvis is still initializing.")
        return

    try:
        from core.os_engine import os_engine

        ai_status = model_manager.get_status()
        ollama_status = "🟢 ON" if ai_status.get("ollama_running") else "🔴 OFF"
        os_report = os_engine.get_system_health()

        diag_text = (
            "🤖 *Jarvis Diagnostics*\n"
            f"• Ollama Core: {ollama_status}\n"
            f"• Active Model: `{ai_status.get('current_model', 'unknown')}`\n"
            f"• Neural Path: `{getattr(config, 'OLLAMA_HOST', 'unknown')}`\n"
            f"• Timezone: `{BOT_TZ.key}`\n"
            f"• Subscribers: `{len(get_subs())}`\n"
            f"• Cache: `{'ON' if CACHE_ENABLED else 'OFF'}`\n"
            f"• Admin IDs: `{len(ADMIN_IDS)}`\n\n"
            f"{os_report}"
        )
        await safe_reply(update, diag_text, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        logger.exception("Status command failed.")
        await safe_reply(update, "⚠️ Diagnostics failed. Check the bot log.")


async def open_app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Launch one explicitly allowlisted desktop application.

    This command is intentionally admin-only. Passing arbitrary shell commands
    from Telegram would create a remote-code-execution surface.
    """
    telegram_id = update.effective_user.id
    if not is_admin(telegram_id):
        logger.warning("Unauthorized /open attempt by Telegram user %s", telegram_id)
        await safe_reply(update, "⛔ This command is restricted to administrators.")
        return

    if not context.args:
        await safe_reply(
            update,
            "🚀 Usage: `/open chrome`\n"
            f"Allowed: {', '.join(sorted(APP_ALLOWLIST))}",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    app_name = " ".join(context.args).strip().lower()
    if app_name not in APP_ALLOWLIST:
        await safe_reply(
            update,
            "⛔ Application is not in the launcher allowlist.",
        )
        return

    try:
        from core.os_engine import os_engine

        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: os_engine.launch_app(app_name),
        )
        await safe_reply(update, str(result))
    except Exception:
        logger.exception("Application launch failed for %r", app_name)
        await safe_reply(update, "⚠️ Application launch failed.")


async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available skills from the skills registry."""
    try:
        from core.skills_registry import skills_registry
        skills_registry.discover_and_load_skills()
        if not skills_registry.skills:
            await safe_reply(update, "⚠️ No skills currently registered.")
            return

        out = "🛠️ *Registered Jarvis Skills*\n\n"
        for s_id, s_info in sorted(skills_registry.skills.items()):
            manifest = s_info.get("manifest", {})
            name = manifest.get("name", s_id)
            desc = manifest.get("description", "No description.")
            clearance = manifest.get("required_clearance", "LOW")
            out += f"• *`{s_id}`* — {name}\n  _{desc}_\n  _Clearance:_ `{clearance}`\n\n"
        out += "Run any skill with: `/run_skill <skill_id>`"
        await safe_reply(update, out, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        logger.exception("Skills command failed.")
        await safe_reply(update, "⚠️ Failed to fetch registered skills.")


async def run_skill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute a registered skill."""
    if not context.args:
        await safe_reply(
            update,
            "Usage: `/run_skill <skill_id>` (e.g. `/run_skill optimize_system`)",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    skill_id = context.args[0].strip()
    status_msg = await safe_reply(update, f"⚡ Executing skill `{skill_id}`...", parse_mode=constants.ParseMode.MARKDOWN)

    try:
        from core.skills_registry import skills_registry
        skills_registry.discover_and_load_skills()
        
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None,
            lambda: skills_registry.execute_skill(
                skill_id,
                {"clearance_level": "HIGH", "args": {}}
            ),
        )

        if res.get("success"):
            import json
            result_str = json.dumps(res.get("result", {}), indent=2)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + "... (truncated)"
            await edit_status(
                status_msg,
                f"✅ *Skill `{skill_id}` Executed Successfully*\n```json\n{result_str}\n```"
            )
        else:
            err = res.get("error", "Unknown error")
            await edit_status(
                status_msg,
                f"❌ *Skill `{skill_id}` Failed*\n_{err}_"
            )
    except Exception:
        logger.exception("Run skill command failed for %s", skill_id)
        await safe_reply(update, f"⚠️ Failed executing skill `{skill_id}`.")


# ---------------------------------------------------------------------------
# Instagram Creator Hub
# ---------------------------------------------------------------------------

async def ig_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if instagram_engine is None:
        await safe_reply(update, "⚠️ Instagram engine is not initialized.")
        return

    await safe_reply(update, "📊 Scanning Instagram Grid...")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, instagram_engine.analyze_performance
        )
        await send_chunked(update, str(result))
    except Exception:
        logger.exception("Instagram analytics failed.")
        await safe_reply(update, "⚠️ Instagram analytics failed.")


async def ig_ideas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if instagram_engine is None:
        await safe_reply(update, "⚠️ Instagram engine is not initialized.")
        return

    await safe_reply(update, "💡 Synthesizing viral concepts...")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, instagram_engine.generate_viral_ideas
        )
        await send_chunked(update, str(result))
    except Exception:
        logger.exception("Instagram idea generation failed.")
        await safe_reply(update, "⚠️ Instagram idea generation failed.")


async def ig_caption_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = normalize_user_text(" ".join(context.args))
    if not topic:
        await safe_reply(
            update,
            "📝 Usage: `/ig_caption Sukuna edit`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    if instagram_engine is None:
        await safe_reply(update, "⚠️ Instagram engine is not initialized.")
        return

    await safe_reply(update, "✍️ Drafting caption...")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: instagram_engine.draft_caption(topic),
        )
        await send_chunked(update, str(result))
    except Exception:
        logger.exception("Instagram caption generation failed.")
        await safe_reply(update, "⚠️ Caption generation failed.")


# ---------------------------------------------------------------------------
# Media handlers
# ---------------------------------------------------------------------------

def media_path(directory: Any, prefix: str, suffix: str) -> Path:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{prefix}_{uuid.uuid4().hex[:12]}{suffix}"


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming photos via vision analysis or image editing."""
    if update.message is None:
        return

    user_id = str(update.effective_user.id)
    caption = normalize_user_text(update.message.caption or "")
    img_path = media_path(
        getattr(config, "DATA_DIR", "data"),
        f"tg_input_{user_id}",
        ".png",
    )

    try:
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(str(img_path))
        await update.message.chat.send_action(constants.ChatAction.TYPING)

        edit_keywords = (
            "edit", "change", "modify", "make it", "style",
            "transform", "remove", "replace", "add",
        )
        is_edit_intent = any(
            keyword in caption.lower() for keyword in edit_keywords
        )

        if is_edit_intent:
            await safe_reply(update, "✏️ Editing image...")
            await handle_message(
                update,
                context,
                forced_message=f"edit image {caption}".strip(),
            )
        else:
            if model_manager is None:
                raise RuntimeError("Model manager is not initialized.")

            await safe_reply(update, "👁️ Analyzing image...")
            loop = asyncio.get_running_loop()
            analysis = await loop.run_in_executor(
                None,
                lambda: model_manager.generate_vision(
                    caption or "What is this?",
                    str(img_path),
                ),
            )
            await send_chunked(update, f"🤖 Vision Report:\n\n{analysis}")

    except Exception:
        logger.exception("Media handler failed for user %s", user_id)
        await safe_reply(update, "⚠️ Failed to process the image.")
    finally:
        try:
            img_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove temporary image %s", img_path)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe a Telegram voice message and feed it into the chat pipeline."""
    if update.message is None or voice_engine is None:
        await safe_reply(update, "⚠️ Voice engine is not available.")
        return

    path = media_path(
        getattr(config, "VOICE_DIR", "data/voice"),
        "tg_voice",
        ".oga",
    )

    try:
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(str(path))
        await update.message.chat.send_action(constants.ChatAction.TYPING)

        result = await voice_engine.transcribe(str(path))
        if result.get("status") != "success":
            logger.error("STT Error: %s", result)
            await safe_reply(update, "⚠️ I couldn't transcribe that voice message.")
            return

        transcript = normalize_user_text(result.get("text", ""))
        await safe_reply(update, f"🎤 Transcribed:\n{transcript}")
        await handle_message(update, context, forced_message=transcript)

    except Exception:
        logger.exception("Voice handler failed.")
        await safe_reply(update, "⚠️ Voice processing failed.")
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Chat pipeline
# ---------------------------------------------------------------------------

def is_image_request(text: str) -> bool:
    """
    Detect explicit visual generation requests without treating every mention
    of a car/logo/etc. as an image command.
    """
    normalized = (text or "").strip().lower()
    if not normalized:
        return False

    # 1. Slash command variations: /image, / image, /img, /imagine, /photo, /picture, /draw, /paint, /render
    if re.match(r"^/\s*(?:image|img|imagine|photo|picture|pic|draw|paint|render|visualize)\b", normalized):
        return True

    # 2. General slash with non-system commands e.g. "/ dog set on ground"
    NON_IMAGE_COMMANDS = {
        "start", "help", "menu", "status", "vitals", "mode", "clear", "reset",
        "chat", "code", "intel", "security", "research", "settings", "tools", "web"
    }
    if normalized.startswith("/"):
        slash_token_match = re.match(r"^/\s*([a-zA-Z0-9_-]+)", normalized)
        if slash_token_match:
            cmd_token = slash_token_match.group(1).lower()
            if cmd_token not in NON_IMAGE_COMMANDS:
                return True

    patterns = [
        r"^(?:please\s+)?(?:create|make|generate|draw|paint|render|design)\s+(?:an?\s+)?(?:image|picture|photo|photograph|art|poster|portrait|wallpaper)\b",
        r"^(?:please\s+)?(?:create|make|generate|draw|paint|render|design)\s+(?:an?\s+)?(?:realistic|anime|cyberpunk|3d|cinematic)\b.*\b(?:image|art|portrait|poster)\b",
        r"^(?:please\s+)?(?:draw|paint|sketch)\s+(?:me\s+)?(?:an?\s+)?",
        r"^(?:photo|photograph|picture|image)\s+of\b",
        r"^(?:a\s+)?(?:breathtaking|stunning|cinematic|photorealistic|hyperrealistic|realistic|4k|8k|ultra-detailed)\s+(?:photograph|photo|image|portrait|picture)\s+of\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def extract_image_prompt(text: str) -> str:
    """Remove only the leading image command; never globally delete words."""
    raw = (text or "").strip()

    # Slash command prefixes
    slash_match = re.match(r"^/\s*(?:image|img|imagine|photo|picture|pic|draw|paint|render|visualize)[:\s]*(.*)$", raw, re.IGNORECASE | re.DOTALL)
    if slash_match:
        p = slash_match.group(1).strip()
        return p or "a high-quality cinematic image"

    # Other slash command like "/ dog set on ground"
    if raw.startswith("/"):
        p = re.sub(r"^/\s*", "", raw).strip()
        if p:
            return p

    # Natural language prefix removal
    nl_prefixes = [
        r"^(?:please\s+)?(?:generate|create|make|render)\s+(?:an?\s+)?(?:image|picture|photo|photograph|wallpaper|illustration|art)\s+(?:of|showing|depicting|with)?\s*",
        r"^(?:please\s+)?(?:draw|paint|sketch)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|illustration|painting)?\s*(?:of)?\s*",
        r"^(?:take|snap)\s+(?:a\s+)?(?:photo|picture)\s+of\s*",
        r"^(?:photo|photograph|picture|image)\s+of\s*",
    ]
    for pattern in nl_prefixes:
        raw = re.sub(pattern, "", raw, count=1, flags=re.IGNORECASE)

    return raw.strip() or "a high-quality cinematic image"


async def generate_images(update: Update, prompt: str) -> None:
    """Generate three variations while isolating failures per variation."""
    from core.image_engine import ImageGenerator

    generator = ImageGenerator()
    loop = asyncio.get_running_loop()

    await update.message.chat.send_action(constants.ChatAction.UPLOAD_PHOTO)

    successes = 0
    for index in range(3):
        try:
            var_prompt = prompt if index == 0 else f"{prompt} variation {index + 1}"
            result = await loop.run_in_executor(
                None,
                lambda p=var_prompt: generator.generate(p),
            )
            if result.get("status") != "success":
                logger.warning("Image generation %d failed: %s", index + 1, result)
                continue

            path = Path(result.get("path", ""))
            if not path.is_file():
                logger.warning("Image generator returned missing path: %s", path)
                continue

            with path.open("rb") as photo:
                await update.message.reply_photo(photo)
            successes += 1
        except Exception:
            logger.exception("Image variation %d failed.", index + 1)

    if successes == 0:
        await safe_reply(update, "⚠️ Image generation failed for all variations.")


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    forced_message: Optional[str] = None,
    execution_mode: Optional[str] = None,
):
    """Main Telegram text pipeline with professional operating mode routing."""
    if update.message is None:
        return

    message = normalize_user_text(forced_message or update.message.text or "")
    if not message:
        return

    user_id = str(update.effective_user.id)
    numeric_user_id = update.effective_user.id

    if not await check_rate_limit(numeric_user_id):
        await safe_reply(
            update,
            "⏳ Too many requests in a short period. Please wait a moment.",
        )
        return

    # Determine active operating mode (per-turn execution_mode or persistent user mode)
    active_mode = (
        execution_mode
        or context.user_data.get("operating_mode")
        or get_user_mode(numeric_user_id)
        or "ai"
    )
    if active_mode not in OPERATING_MODES:
        active_mode = "ai"
    mode_info = OPERATING_MODES[active_mode]

    # Explicit image requests bypass normal chat generation.
    if is_image_request(message):
        try:
            await generate_images(update, extract_image_prompt(message))
        except Exception:
            logger.exception("Image generation pipeline failed.")
            await safe_reply(update, "⚠️ Image generation failed.")
        return

    status_msg = await safe_reply(update, f"⚡ [{mode_info['icon']} {mode_info['name']}] Processing...")

    # Persist simple entertainment taste signals.
    text_lower = message.lower()
    if "anime" in text_lower:
        update_user_taste(user_id, "anime")
    elif "kdrama" in text_lower or "k-drama" in text_lower:
        update_user_taste(user_id, "kdrama")
    elif "movie" in text_lower:
        update_user_taste(user_id, "movie")

    # Cache only with a user-scoped key. Disabled by default.
    cache_key = (
        f"tg:{user_id}:"
        f"mode:{active_mode}:"
        f"{message.strip().lower()}"
    )
    if CACHE_ENABLED:
        try:
            cached = global_cache.get(cache_key)
            if cached:
                await edit_status(status_msg, cached)
                return
        except Exception:
            logger.debug("Cache lookup failed.", exc_info=True)

    await update.message.chat.send_action(constants.ChatAction.TYPING)

    if processing_semaphore is None:
        raise RuntimeError("Request semaphore is not initialized.")

    async with processing_semaphore:
        try:
            if brain is None or flask_app is None:
                raise RuntimeError("Jarvis core is not initialized.")

            # Load DB values for compatibility/telemetry. We deliberately keep
            # only primitive data rather than passing a detached ORM instance.
            user_data = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: get_db_user_data(user_id),
            )

            response_holder: list[str] = []

            def _generate() -> None:
                # Brain is the authoritative conversation pipeline.
                # Mode-specific instructions and autonomous multi-phase routing
                # are handled by the Jarvis Brain node.
                response = brain.process(
                    message,
                    user_id=f"tg_{user_id}",
                    mode=active_mode,
                )
                response_holder.append(str(response or ""))

            await asyncio.get_running_loop().run_in_executor(None, _generate)
            full_response = response_holder[0].strip()

            # ----------------------------------------------------------------
            # Media delivery protocol
            # ----------------------------------------------------------------
            image_matches = re.findall(
                r"IMAGE_\d+:\s+(.*?)\s+\|\s+URL:",
                full_response,
            )

            for raw_path in image_matches:
                path = Path(raw_path.strip())
                try:
                    if path.is_file():
                        await update.message.chat.send_action(
                            constants.ChatAction.UPLOAD_PHOTO
                        )
                        with path.open("rb") as photo:
                            await update.message.reply_photo(photo)
                except Exception:
                    logger.exception("Failed to deliver generated image %s", path)

            if image_matches:
                full_response = re.sub(
                    r"IMAGE_\d+:.*?\n",
                    "",
                    full_response,
                )
                full_response = full_response.replace(
                    "SUCCESS: HD Image variations generated.",
                    "🎨 HD Art Pack Synthesized.",
                )

            # Explicit image edit protocol.
            edit_match = re.search(
                r"SUCCESS:\s*Image edited successfully\.\s*File:\s*(\S+)",
                full_response,
                flags=re.IGNORECASE,
            )
            if edit_match:
                filename = Path(edit_match.group(1)).name
                image_dir = Path(getattr(config, "IMAGE_GEN_DIR", "data/images"))
                local_path = image_dir / filename

                if local_path.is_file():
                    try:
                        with local_path.open("rb") as photo:
                            await update.message.reply_photo(
                                photo,
                                caption="✨ Modification Complete",
                            )
                    except Exception:
                        logger.exception("Failed to deliver edited image.")

                full_response = "Image transformation successful. See the image above."

            if not full_response:
                full_response = (
                    "Systems nominal, Boss. How can I assist you today?"
                )

            final_cleaned = full_response.strip()

            if CACHE_ENABLED:
                try:
                    global_cache.set(cache_key, final_cleaned)
                except Exception:
                    logger.debug("Cache write failed.", exc_info=True)

            # Safeguard large responses by chunking if exceeding Telegram limits
            if len(final_cleaned) > 3900:
                await edit_status(status_msg, final_cleaned[:3900])
                await send_chunked(update, final_cleaned[3900:])
            else:
                await edit_status(status_msg, final_cleaned)

            # Optional TTS.
            if context.user_data.get("voice_mode", False) and voice_engine:
                try:
                    await update.message.chat.send_action(
                        constants.ChatAction.RECORD_VOICE
                    )
                    speech_text = plain_text(full_response)
                    if len(speech_text) > 800:
                        speech_text = speech_text[:800] + "..."

                    voice_result = await voice_engine.speak(speech_text)
                    if voice_result.get("status") == "success":
                        voice_dir = Path(
                            getattr(config, "VOICE_DIR", "data/voice")
                        )
                        voice_path = voice_dir / voice_result["filename"]
                        if voice_path.is_file():
                            with voice_path.open("rb") as voice_file:
                                await update.message.reply_voice(voice_file)
                            voice_path.unlink(missing_ok=True)
                except Exception:
                    logger.exception("Voice synthesis failed.")

            # Predictive suggestions (best-effort)
            try:
                # Throttle to 10% chance to prevent spamming the user on every message
                if random.random() < 0.10 and chat_engine and recommender:
                    preferences = user_data.get("preferences", {})
                    general_suggestion = chat_engine.memory.predict_next(
                        preferences
                    )
                    taste_history = preferences.get("entertainment_taste", [])
                    media_suggestion = recommender.get_proactive_suggestion(
                        taste_history
                    )
                    suggestion = media_suggestion or (
                        f"🔮 You might also like: `{general_suggestion}`"
                        if general_suggestion
                        else None
                    )

                    if suggestion and suggestion.lower() not in full_response.lower():
                        await asyncio.sleep(0.5)
                        await safe_reply(update, str(suggestion), parse_mode=constants.ParseMode.MARKDOWN)
            except Exception:
                logger.debug("Proactive suggestion failed.", exc_info=True)

        except Exception:
            logger.exception("Chat failed for user %s", user_id)
            # Direct recovery fallback incorporating active operating mode prompt
            recovered = False
            try:
                if model_manager:
                    now_str = monotonic_time.strftime("%B %d, %Y")
                    mode_prompt = OPERATING_MODES.get(active_mode, OPERATING_MODES["ai"])["prompt"]
                    full_sys = (
                        f"{config.SYSTEM_PROMPT.format(current_date=now_str)}\n\n"
                        f"# OPERATING MODE PROTOCOL:\n{mode_prompt}"
                    )
                    recovery_resp = model_manager.generate(
                        messages=[{"role": "user", "content": message}],
                        system_prompt=full_sys,
                    )
                    if recovery_resp and not recovery_resp.startswith("⚠️"):
                        await edit_status(status_msg, recovery_resp.strip())
                        recovered = True
            except Exception:
                logger.debug("Direct recovery attempt failed.", exc_info=True)

            if not recovered:
                await edit_status(
                    status_msg,
                    "At your service, Boss. All core systems are operational. I encountered a momentary neural link hiccup with that query. How would you like me to proceed?",
                )


# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------

async def daily_news_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Fetch and send a daily intelligence report to subscribers."""
    if chat_engine is None:
        logger.error("Daily broadcast skipped: chat engine is not initialized.")
        return

    subscribers = get_subs()
    if not subscribers:
        logger.info("Daily broadcast skipped: no subscribers.")
        return

    logger.info("Starting scheduled daily news broadcast.")

    class SystemUser:
        id = "system"
        username = "system_scheduler"
        preferences: dict[str, Any] = {}

    query = "latest top headlines in technology and world news"
    response_chunks: list[str] = []

    try:
        def _generate() -> None:
            for chunk in chat_engine.chat_stream(
                query,
                SystemUser(),
                "daily_broadcast",
            ):
                response_chunks.append(str(chunk))

        await asyncio.get_running_loop().run_in_executor(None, _generate)
        news_report = "".join(response_chunks).strip()
    except Exception:
        logger.exception("Daily news generation failed.")
        news_report = ""

    media_lines: list[str] = []
    if recommender:
        try:
            kdrama = recommender.recommend("kdrama") or []
            anime = recommender.recommend("anime") or []
            if kdrama:
                media_lines.append(f"• K-Drama: `{kdrama[0]}`")
            if anime:
                media_lines.append(f"• Anime: `{anime[0]}`")
        except Exception:
            logger.exception("Trending media recommendation failed.")

    parts = ["📰 *DAILY INTELLIGENCE REPORT*"]
    if news_report:
        parts.append(news_report)
    if media_lines:
        parts.append("🎬 *TRENDING PICKS*\n" + "\n".join(media_lines))

    report = "\n\n".join(parts)

    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=report[:3900],
                parse_mode=constants.ParseMode.MARKDOWN,
            )
        except TelegramError as exc:
            logger.warning(
                "Daily report delivery failed for %s: %s",
                chat_id,
                exc,
            )
        except Exception:
            logger.exception("Unexpected daily report delivery failure.")


async def audit_missions(context: ContextTypes.DEFAULT_TYPE):
    """Scan pending missions and send a concise proactive nudge."""
    if flask_app is None:
        return

    subscribers = get_subs()
    if not subscribers:
        return

    logger.info("Executing Proactive Mission Audit...")

    try:
        from models import Mission

        with flask_app.app_context():
            pending = (
                Mission.query
                .filter_by(status="pending")
                .order_by(Mission.priority.desc())
                .all()
            )

            if not pending:
                logger.info("Mission audit complete: no pending missions.")
                return

            high_priority = [m for m in pending if m.priority == 3]
            count = len(pending)

            if high_priority:
                mission = high_priority[0]
                message = (
                    "🏹 *Stark Intelligence Briefing*\n\n"
                    f"You have `{count}` incomplete missions.\n"
                    f"Most critical: *{mission.title}*\n\n"
                    "Use `/nudge` again when you want another mission scan."
                )
            else:
                message = (
                    "🛰️ *Mission Monitor*\n\n"
                    f"You have `{count}` pending tasks."
                )

        for chat_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=constants.ParseMode.MARKDOWN,
                )
            except TelegramError as exc:
                logger.warning("Mission nudge failed for %s: %s", chat_id, exc)

    except Exception:
        logger.exception("Mission audit failed.")


# ---------------------------------------------------------------------------
# Error handling / lifecycle
# ---------------------------------------------------------------------------

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    error = context.error

    if isinstance(error, Conflict):
        logger.warning(
            "Telegram polling conflict. Another bot process may be using the same token."
        )
        return

    if isinstance(error, NetworkError):
        logger.warning("Telegram network disruption: %s", error)
        return

    logger.error("Telegram update error: %s", error, exc_info=error)


def validate_runtime_configuration() -> bool:
    """Fail early for critical missing configuration."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", None)
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is missing.")
        return False

    if not ADMIN_IDS:
        logger.warning(
            "No Telegram admin IDs configured. /open will remain disabled."
        )

    return True


def main() -> None:
    """Start the Jarvis Telegram node."""
    global processing_semaphore

    if not TELEGRAM_AVAILABLE:
        logger.error(
            "Startup aborted: install python-telegram-bot and its JobQueue extras."
        )
        return

    if not validate_runtime_configuration():
        return

    # Create asyncio primitives after entering the actual application runtime.
    processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    try:
        init_jarvis()

        token = config.TELEGRAM_BOT_TOKEN
        app = (
            Application.builder()
            .token(token)
            .concurrent_updates(True)
            .build()
        )

        app.add_error_handler(error_handler)

        # JobQueue is provided by APScheduler through python-telegram-bot extras.
        if app.job_queue:
            app.job_queue.run_daily(
                daily_news_broadcast,
                time=dt_time(hour=9, minute=0, tzinfo=BOT_TZ),
                name="daily_news_broadcast",
            )
            app.job_queue.run_repeating(
                audit_missions,
                interval=4 * 60 * 60,
                first=5 * 60,
                name="mission_auditor",
            )
            logger.info(
                "Scheduled jobs enabled: daily news 09:00 %s; mission audit every 4h.",
                BOT_TZ.key,
            )
        else:
            logger.warning(
                "JobQueue unavailable. Install python-telegram-bot[job-queue] "
                "to enable scheduled jobs."
            )

        # Commands
        handlers = [
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CommandHandler("search", search_command),
            CommandHandler("news", news_command),
            CommandHandler("subscribe", subscribe_command),
            CommandHandler("unsubscribe", unsubscribe_command),
            CommandHandler("image", image_command),
            CommandHandler("video", video_command),
            CommandHandler("new", new_command),
            CommandHandler("voice", voice_command),
            CommandHandler("mode", mode_command),
            CommandHandler("ai", ai_command),
            CommandHandler("chat", chat_command),
            CommandHandler("code", code_command),
            CommandHandler("creative", creative_command),
            CommandHandler("security", security_command),
            CommandHandler("research", research_command),
            CommandHandler("status", status_command),
            CommandHandler("open", open_app_command),
            CommandHandler("nudge", nudge_command),
            CommandHandler("ig_analytics", ig_analytics_command),
            CommandHandler("ig_ideas", ig_ideas_command),
            CommandHandler("ig_caption", ig_caption_command),
            CommandHandler("skills", skills_command),
            CommandHandler("run_skill", run_skill_command),
        ]
        for handler in handlers:
            app.add_handler(handler)

        app.add_handler(CallbackQueryHandler(mode_button_callback, pattern=r"^mode:"))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        logger.info("=" * 64)
        logger.info("  JARVIS PROFESSIONAL — TELEGRAM NODE ACTIVE")
        logger.info("  Timezone: %s | Concurrent requests: %d", BOT_TZ.key, MAX_CONCURRENT_REQUESTS)
        logger.info("=" * 64)

        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

    except KeyboardInterrupt:
        logger.info("Jarvis Telegram node stopped by operator.")
    except Exception:
        logger.exception("Fatal Telegram node error.")
        raise


if __name__ == "__main__":
    main()
