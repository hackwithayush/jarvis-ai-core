@echo off
title Install JARVIS 24/7 Windows Auto-Boot
color 0B

cd /d "%~dp0"

echo ====================================================================
echo        REGISTERING JARVIS 24/7 FOR AUTOMATIC WINDOWS AUTO-BOOT
echo ====================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File register_autostart.ps1

echo.
echo ====================================================================
echo [STATUS]: JARVIS is now registered to start 24/7 automatically
echo           every time Windows boots or when you log in.
echo ====================================================================
echo.
pause
