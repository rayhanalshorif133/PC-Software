@echo off
title Video to Image Converter
cd /d "%~dp0"

echo [1/2] Checking Python environment...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [2/2] Starting Video to Image Converter...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while running the application.
    pause
)

