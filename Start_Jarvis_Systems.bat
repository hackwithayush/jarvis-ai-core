@echo off
title JARVIS Intelligence Grid Launcher
color 0B

if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat

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
echo   [0] Launch 3-Agent Adversarial Review CLI (/review)
echo   [1] Boot Terminal Interface (Direct Chat)
echo   [2] Boot Web Interface (Full UI)
echo   [3] Boot Telegram Agent (Mobile Access)
echo   [4] Run Neural Diagnostics (Test Routing)
echo   [5] Boot Web and Telegram Together
echo   [6] Boot 24/7 Guardian Supervisor (Auto-Healing Web + Telegram)
echo   [7] Install 24/7 Windows Auto-Boot (Runs on Startup)
echo   [8] Stop All 24/7 Nodes
echo   [9] Power Down (Exit)
echo.

set /p choice="Enter Command (0-9): "

if "%choice%"=="0" goto reviewcli
if "%choice%"=="1" goto terminal
if "%choice%"=="2" goto web
if "%choice%"=="3" goto telegram
if "%choice%"=="4" goto diag
if "%choice%"=="5" goto both
if "%choice%"=="6" goto guardian247
if "%choice%"=="7" goto installboot
if "%choice%"=="8" goto stopnodes
if "%choice%"=="9" goto exit

echo Invalid command. Try again.
timeout /t 2 >nul
goto menu

:reviewcli
cls
echo [JARVIS]: Launching 3-Agent Adversarial Review CLI...
python -u review.py
echo.
pause
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

:both
cls
echo [JARVIS]: Booting Web Interface and Telegram Agent in parallel neural nodes...
start "JARVIS Web Interface" python app.py
start "JARVIS Telegram Agent" python telegram_bot.py
echo [JARVIS]: Both nodes initialized in separate terminal windows.
echo.
pause
goto menu

:guardian247
cls
echo [JARVIS]: Booting 24/7 Autonomous Guardian Supervisor...
python jarvis_guardian.py
echo.
pause
goto menu

:installboot
cls
call install_autostart_24_7.bat
goto menu

:stopnodes
cls
call stop_jarvis_24_7.bat
goto menu

:exit
cls
echo [JARVIS]: Powering down systems. Goodbye, Boss.
timeout /t 2 >nul
exit
