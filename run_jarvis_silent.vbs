' JARVIS 24/7 Silent Background Launcher
' Runs JARVIS Guardian using pythonw without launching cmd.exe
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strCurrentDir = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.CurrentDirectory = strCurrentDir

Dim pythonExe
If fso.FileExists(strCurrentDir & "\.venv\Scripts\pythonw.exe") Then
    pythonExe = """" & strCurrentDir & "\.venv\Scripts\pythonw.exe"""
ElseIf fso.FileExists(strCurrentDir & "\.venv\Scripts\python.exe") Then
    pythonExe = """" & strCurrentDir & "\.venv\Scripts\python.exe"""
Else
    pythonExe = "pythonw"
End If

' 0 = Hide window, False = Do not wait for script to terminate
WshShell.Run pythonExe & " """ & strCurrentDir & "\jarvis_guardian.py""", 0, False
Set WshShell = Nothing
Set fso = Nothing
