' JARVIS 24/7 Silent Background Launcher
' Runs JARVIS Web and Telegram supervisor completely invisible without a command prompt window.
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strCurrentDir = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = strCurrentDir
' 0 = Hide window, False = Do not wait for script to terminate
WshShell.Run "cmd /c run_jarvis_24_7.bat", 0, False
Set WshShell = Nothing
Set fso = Nothing
