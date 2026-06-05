@echo off
title JARVIS Visual Interface Loader
echo =======================================================
echo          MOUNTING JARVIS DESKTOP COMPANION
echo =======================================================

echo [JARVIS UI] Starting Real-time WebSocket Backend...
start "JARVIS UI Backend" /B python UI\backend\api.py

echo [JARVIS UI] Launching Electron Desktop Environment...
cd UI\frontend
npm run electron:dev
