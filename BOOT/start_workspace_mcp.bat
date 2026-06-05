@echo off
title JARVIS GOOGLE WORKSPACE LINK
cd /d "%~dp0.."

echo =======================================================
echo     HOOKING GOOGLE WORKSPACE TO JARVIS VIA MCP
echo =======================================================

:: Check if the token already exists
if exist ".gdrive-server-credentials.json" (
    echo [MCP] Token found. Launching Google Workspace server...
    npx -y @modelcontextprotocol/server-gdrive
) else (
    echo [MCP] First-time authentication required.
    echo [MCP] This will open a browser window for Google Sign-In.
    echo =======================================================
    echo Please log in on the browser page that opens...
    npx -y @modelcontextprotocol/server-gdrive auth
    
    echo =======================================================
    echo [MCP] Authentication complete. Launching server...
    npx -y @modelcontextprotocol/server-gdrive
)

pause
