@echo off
title Stop JARVIS 24/7 Systems
color 0C

echo ====================================================================
echo             STOPPING ALL JARVIS 24/7 BACKGROUND NODES
echo ====================================================================
echo.

echo Halting any active guardian and python nodes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'jarvis_guardian\.py|app\.py|telegram_bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Stopped Process: ' + $_.ProcessId + ' (' + $_.Name + ')') }"

echo.
echo Freeing port 5000 if occupied...
powershell -NoProfile -Command "$conns = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue; if ($conns) { foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('Freed port 5000 from PID: ' + $c.OwningProcess) } } else { Write-Host 'Port 5000 is clean.' }"

echo.
echo [JARVIS]: All 24/7 services have been powered down safely.
timeout /t 3 >nul
