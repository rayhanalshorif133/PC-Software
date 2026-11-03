@echo off
title Pro Downloader - Video & Audio Downloader
echo ===================================================
echo   Pro Downloader - Fast Media Engine
echo ===================================================
echo.

echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org
    pause
    exit /b
)

echo Starting Pro Downloader Desktop App...
python app.py
if %errorlevel% neq 0 (
    echo.
    echo [Notice] Attempting to install missing dependencies...
    python -m pip install -r requirements.txt
    echo Relaunching...
    python app.py
)
