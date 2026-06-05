@echo off
title Jarvis Telegram Bot
cd /d "%~dp0"

:loop
echo [%date% %time%] Starting Jarvis Telegram Bot...
.venv\Scripts\python telegram_bot.py
echo [%date% %time%] Bot crashed or stopped. Restarting in 5 seconds...
timeout /t 5 /noq
goto loop
