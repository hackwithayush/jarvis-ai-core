@echo off
title JARVIS OMEGA :: 3-Agent Adversarial Review CLI
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -u review.py %*
) else (
    python -u review.py %*
)
if "%~1"=="" pause
