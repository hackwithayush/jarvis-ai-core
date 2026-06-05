@echo off
title Building JARVIS Executable
echo =======================================================
echo          COMPILING JARVIS AI OPERATING SYSTEM
echo =======================================================

if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
)

echo [BUILD] Installing PyInstaller...
python -m pip install pyinstaller

echo [BUILD] Compiling Background Daemon...
:: Compile the startup service into a single hidden window executable (--noconsole for real background daemon)
:: We use normal console for debugging right now
pyinstaller --name "JARVIS" --onefile --icon=NONE ..\ALWAYS_ON_RUNTIME\startup_service.py

echo =======================================================
echo BUILD COMPLETE.
echo Your executable is located in the 'dist' folder.
echo =======================================================
pause
