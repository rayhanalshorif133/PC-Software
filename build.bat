@echo off
setlocal
cd /d "%~dp0"
title Building Auto Clicker Executable...

echo ========================================================
echo        Auto Clicker - Standalone EXE Builder
echo ========================================================
echo.

:: 1. Check Python installation
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Python is not found on your system!
        echo Please install Python and check "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
    set "PY_CMD=py"
) else (
    set "PY_CMD=python"
)

echo [1/3] Using Python:
%PY_CMD% --version
echo.

:: 2. Ensure PyInstaller and required packages are installed
echo [2/3] Checking and installing required dependencies...
%PY_CMD% -m pip install -r requirements.txt pyinstaller --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not install dependencies with pip. Attempting build anyway...
)
echo.

:: 3. Build executable with PyInstaller
echo [3/3] Building AutoClicker.exe (Please wait a moment)...
%PY_CMD% -m PyInstaller --noconfirm AutoClicker.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  [SUCCESS] Auto Clicker EXE built successfully!
    echo ========================================================
    echo.
    echo  Location:
    echo  %~dp0dist\AutoClicker.exe
    echo.
    echo  You can now run AutoClicker.exe directly from the dist folder.
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo  [ERROR] Build failed with error code %ERRORLEVEL%.
    echo  Please check the log output above for details.
    echo ========================================================
)

echo.
pause

