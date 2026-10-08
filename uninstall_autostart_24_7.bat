@echo off
title Remove JARVIS 24/7 Windows Auto-Boot
color 0E

echo Removing JARVIS Auto-Boot shortcut from Windows Startup...
powershell -NoProfile -Command ^
    "$startupPath = [Environment]::GetFolderPath('Startup'); " ^
    "$shortcutPath = Join-Path $startupPath 'JARVIS_24_7_AutoBoot.lnk'; " ^
    "if (Test-Path $shortcutPath) { Remove-Item $shortcutPath -Force; Write-Host '✅ JARVIS Auto-Boot shortcut removed.' } else { Write-Host 'Shortcut was not present in Startup folder.' }"

echo.
pause
