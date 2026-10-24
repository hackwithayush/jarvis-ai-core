@echo off
:: ====================================================================
:: Windows System Integrity & Corruption Auto-Repair Tool
:: Performs DISM Component Store Restore, SFC Scan, and Disk Health Fix
:: ====================================================================

title Windows System File Integrity & Corruption Repair

:: Check for administrative privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [REQUESTING ELEVATION] Administrative privileges are required.
    echo Prompting for User Account Control (UAC) elevation...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

color 0A
cls
echo ====================================================================
echo      WINDOWS SYSTEM INTEGRITY & COMPONENT STORE REPAIR UTILITY
echo ====================================================================
echo.
echo [1/5] Checking DISM Component Store Health...
DISM /Online /Cleanup-Image /ScanHealth
echo.

echo [2/5] Restoring Component Store and Repairing Corrupted Packages...
DISM /Online /Cleanup-Image /RestoreHealth
echo.

echo [3/5] Running System File Checker (SFC /scannow)...
sfc /scannow
echo.

echo [4/5] Cleaning up Superseded Servicing Packages...
DISM /Online /Cleanup-Image /StartComponentCleanup
echo.

echo [5/5] Checking Filesystem Integrity on C: ...
chkdsk C: /scan
echo.

echo ====================================================================
echo [STATUS]: Comprehensive System Integrity & Corruption Repair Finished!
echo ====================================================================
echo.
pause
