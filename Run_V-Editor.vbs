Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Check if V-Editor.exe exists and try running it
Dim fso, exePath
Set fso = CreateObject("Scripting.FileSystemObject")
exePath = WshShell.CurrentDirectory & "\dist\V-Editor\V-Editor.exe"

If fso.FileExists(exePath) Then
    ' Unblock and run exe silently
    WshShell.Run "powershell -WindowStyle Hidden -Command ""Unblock-File -Path '" & exePath & "'""", 0, True
    WshShell.Run """" & exePath & """", 1, False
Else
    ' Fallback to windowless pythonw
    WshShell.Run "pythonw app.py", 0, False
End If

