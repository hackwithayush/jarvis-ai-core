"""
Jarvis Telegram Bot — Professional Edition
==========================================

Canonical entry point for the upgraded Jarvis Telegram Bot with
six professional operating modes, inline keyboard selection, persistent
mode state, mode-specific instructions, and autonomous AI routing.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Re-export and execute the complete professional implementation
from telegram_bot import *  # noqa: F401, F403
import telegram_bot

if __name__ == "__main__":
    telegram_bot.main()
