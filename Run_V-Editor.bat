@echo off
title V-Editor Launcher
cd /d "%~dp0"

echo [1/2] Unblocking executable security flags...
powershell -NoProfile -Command "if (Test-Path 'dist\V-Editor\V-Editor.exe') { Unblock-File -Path 'dist\V-Editor\V-Editor.exe' }"

echo [2/2] Starting V-Editor Desktop Application...
if exist "dist\V-Editor\V-Editor.exe" (
    start "" "dist\V-Editor\V-Editor.exe"
    exit
)

if exist "app.py" (
    start "" pythonw app.py
    exit
)

pause
