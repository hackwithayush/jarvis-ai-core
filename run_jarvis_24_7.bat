@echo off
title JARVIS 24/7 Autonomous Operating System (Web + Telegram)
color 0A

:: Change to script directory
cd /d "%~dp0"

echo ====================================================================
echo        JARVIS 24/7 AUTONOMOUS GUARDIAN SUPERVISOR (v16.0)
echo ====================================================================
echo.
echo [NODES MONITORED]
echo  - Web Gateway:      http://localhost:5000
echo  - Telegram Agent:   Autonomous Mobile Neural Link
echo  - Auto-Recovery:    Active (Instant Restart on Crash)
echo  - Alert Channel:    Gmail (ayushchaudhary22790@gmail.com)
echo.
echo Initializing environment...

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

:: Launch the Guardian
python jarvis_guardian.py

echo.
echo JARVIS 24/7 Guardian exited.
pause
