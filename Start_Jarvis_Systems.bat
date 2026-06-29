@echo off
title JARVIS Intelligence Grid Launcher
color 0B

:menu
cls
echo =======================================================
echo          JARVIS SENTIENT OPERATING SYSTEM (v16.0)
echo =======================================================
echo.
echo [SYSTEM STATUS]
echo - Core Neural Pathways: ONLINE
echo - Cloud Nodes (Groq/Gemini/OpenRouter): ACTIVE
echo - Cognitive Level: GPT-5.5 Equivalent
echo.
echo What are your orders, Boss?
echo.
echo   [1] Boot Terminal Interface (Direct Chat)
echo   [2] Boot Web Interface (Full UI)
echo   [3] Boot Telegram Agent (Mobile Access)
echo   [4] Run Neural Diagnostics (Test Routing)
echo   [5] Power Down (Exit)
echo.

set /p choice="Enter Command (1-5): "

if "%choice%"=="1" goto terminal
if "%choice%"=="2" goto web
if "%choice%"=="3" goto telegram
if "%choice%"=="4" goto diag
if "%choice%"=="5" goto exit

echo Invalid command. Try again.
timeout /t 2 >nul
goto menu

:terminal
cls
echo [JARVIS]: Booting Terminal Neural Link...
python terminal_jarvis.py
echo.
pause
goto menu

:web
cls
echo [JARVIS]: Booting Web Interface on local host...
python app.py
echo.
pause
goto menu

:telegram
cls
echo [JARVIS]: Connecting to Telegram Servers...
python telegram_bot.py
echo.
pause
goto menu

:diag
cls
echo [JARVIS]: Running Cloud Node Diagnostics...
python test_routing.py
echo.
pause
goto menu

:exit
cls
echo [JARVIS]: Powering down systems. Goodbye, Boss.
timeout /t 2 >nul
exit
