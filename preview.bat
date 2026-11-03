@echo off
cd /d "%~dp0"
echo Starting Auto Clicker (Python Preview Mode)...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Press any key to exit.
    pause
)

