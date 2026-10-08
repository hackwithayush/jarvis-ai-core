@echo off
title JARVIS - Git Push to Cloud Repository
color 0b
echo =====================================================================
echo    JARVIS v16.0 -- Pushing Latest Code to GitHub Cloud Repository
echo =====================================================================
echo.

cd /d "%~dp0"
echo [1/3] Current Directory: %CD%
echo [2/3] Verifying Git Status...
git status -s

echo.
echo [3/3] Pushing to origin main...
git push origin main

echo.
if %errorlevel% equ 0 (
    echo =====================================================================
    echo  SUCCESS: Your latest JARVIS code has been pushed to GitHub!
    echo  Render or your cloud service will now automatically deploy.
    echo =====================================================================
) else (
    echo =====================================================================
    echo  NOTICE: If prompted for GitHub login, please sign in via browser.
    echo =====================================================================
)

pause
