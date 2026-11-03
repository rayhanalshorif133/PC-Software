@echo off
title Build Standalone Windows EXE
cd /d "%~dp0"

echo ========================================================
echo   Video to Image Converter - Windows EXE Builder
echo ========================================================
echo.

echo [1/3] Checking PyInstaller...
python -m PyInstaller --version >nul 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo [2/3] Building standalone executable (onefile)...
python -m PyInstaller --noconsole --onefile --name "VideoToImage" --collect-all customtkinter main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output messages above.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [3/3] Build Successful!
echo Your executable is ready at: dist\VideoToImage.exe
echo ========================================================
echo.
pause

