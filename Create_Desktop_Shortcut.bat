@echo off
setlocal
echo Creating Desktop Shortcut for VideoFrame Pro...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$s = $ws.CreateShortcut((Join-Path $desktop 'VideoFrame Pro.lnk')); " ^
  "$s.TargetPath = (Resolve-Path '%~dp0dist\VideoFramePro\VideoFramePro.exe').Path; " ^
  "$s.WorkingDirectory = (Resolve-Path '%~dp0dist\VideoFramePro').Path; " ^
  "$s.IconLocation = (Resolve-Path '%~dp0assets\app_icon.ico').Path; " ^
  "$s.Description = 'Video to Frames & Person Detection Pro'; " ^
  "$s.Save(); " ^
  "Write-Host 'Desktop Shortcut created successfully on your Desktop!'"

pause
