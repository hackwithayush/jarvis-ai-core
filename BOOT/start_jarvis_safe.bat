@echo off
title JARVIS [SAFE MODE]
echo =======================================================
echo          BOOTING JARVIS IN SAFE MODE
echo          (Autonomous Actions Disabled)
echo =======================================================

:: Environment Setup
echo [BOOT] Activating Python 3.11 Virtual Environment...
call C:\AI\envs\jarvis\Scripts\activate.bat
set PYTHONPATH=%~dp0..

python dependency_check.py
if %ERRORLEVEL% NEQ 0 (
    pause
    exit /b 1
)

:: No autonomous components, no telegram bot, strictly voice/chat loop.
echo [BOOT] Entering isolated Safe Mode environment...
python ..\ALWAYS_ON_RUNTIME\startup_service.py

python shutdown_manager.py
pause
