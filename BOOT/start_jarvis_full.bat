@echo off
title JARVIS AI Operating System
echo =======================================================
echo          BOOTING JARVIS AI OPERATING PLATFORM
echo =======================================================

:: 1. Environment Setup
echo [BOOT] Activating Python 3.11 Virtual Environment...
call C:\AI\envs\jarvis\Scripts\activate.bat

:: Explicitly set the root JARVIS directory into the Python path
set PYTHONPATH=%~dp0..

:: 2. Run Dependency Check
python dependency_check.py
if %ERRORLEVEL% NEQ 0 (
    echo [BOOT ERROR] Dependency check failed. Aborting boot.
    pause
    exit /b 1
)

:: 3. Start VRAM Governor & Health Monitor in background
start "JARVIS HEALTH MONITOR" /MIN python health_check.py
echo [BOOT] Health Monitor initialized.

:: 4. Start Telegram Bot in background
start "JARVIS TELEGRAM" /MIN python ..\TELEGRAM\telegram_bot.py
echo [BOOT] Telegram Remote Service hooked.

:: 5. Start the Visual UI Backend and Frontend
echo [BOOT] Mounting JARVIS Desktop Companion UI...
start "JARVIS UI Backend" /MIN python ..\UI\backend\api.py
start "JARVIS UI Frontend" /MIN cmd /c "cd ..\UI\frontend && npm run electron:dev"

:: 6. Start Autonomous Voice Runtime
echo [BOOT] Starting Main Voice and OS Runtime...
start "JARVIS CORE" /MIN python ..\ALWAYS_ON_RUNTIME\startup_service.py

:: 7. Cleanup on Exit
python shutdown_manager.py
pause
