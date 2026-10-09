@echo off
title JARVIS Web Interface (Port 5000)
color 0B
echo =======================================================
echo          JARVIS WEB INTERFACE SERVER (v16.0)
echo =======================================================
echo.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
echo [JARVIS]: Initializing Web Gateway at http://127.0.0.1:5000 ...
python app.py
if %errorlevel% neq 0 (
    echo.
    echo Server stopped with error.
    pause
)
