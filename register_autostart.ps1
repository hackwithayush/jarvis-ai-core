$ws = New-Object -ComObject WScript.Shell
$startupPath = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupPath 'JARVIS_24_7_AutoBoot.lnk'
$targetScript = Join-Path (Get-Location).Path 'run_jarvis_silent.vbs'

$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = 'wscript.exe'
$shortcut.Arguments = "`"$targetScript`""
$shortcut.WorkingDirectory = (Get-Location).Path
$shortcut.Description = 'JARVIS 24/7 Autonomous Operating System'
$shortcut.Save()

Write-Host "✅ Auto-Boot Shortcut registered successfully at: $shortcutPath"
