@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo        PC-Software Hub - New Branch Creator
echo ========================================================
echo.

set /p BRANCH_NAME="Enter New Software Branch Name (e.g. obs-studio): "

if "%BRANCH_NAME%"=="" (
    echo [ERROR] Branch name cannot be empty!
    pause
    exit /b 1
)

set /p SOFT_TITLE="Enter Display Name (Leave empty to auto-format from branch name): "
if "%SOFT_TITLE%"=="" set SOFT_TITLE=%BRANCH_NAME%

set /p SOFT_VER="Enter Version (e.g. v1.0, or leave empty for Latest): "
if "%SOFT_VER%"=="" set SOFT_VER=Latest

set /p SOFT_CAT="Enter Category [utilities / media / development] (default: utilities): "
if "%SOFT_CAT%"=="" set SOFT_CAT=utilities

echo.
echo [*] Creating orphan branch: %BRANCH_NAME% ...
git checkout --orphan %BRANCH_NAME%

echo [*] Cleaning staging area for fresh software files...
git rm -rf . >nul 2>&1

echo [*] Creating software.json metadata for auto-discovery...
(
echo {
echo   "name": "%SOFT_TITLE%",
echo   "version": "%SOFT_VER%",
echo   "category": "%SOFT_CAT%",
echo   "description": "Portable standalone version of %SOFT_TITLE%. Ready to clone and use.",
echo   "tags": ["Portable", "%SOFT_CAT%", "Windows"]
echo }
) > software.json

echo.
echo [*] Creating placeholder README.md and launch script...
(
echo # %SOFT_TITLE%
echo.
echo ^> **Branch:** `%BRANCH_NAME%`
echo ^> **Repository:** https://github.com/rayhanalshorif133/PC-Software.git
echo.
echo ---
echo.
echo ### 🚀 Direct Clone Command
echo ```bash
echo git clone -b %BRANCH_NAME% --single-branch https://github.com/rayhanalshorif133/PC-Software.git
echo ```
echo.
echo Put your software files, installation scripts, or portable binaries here.
) > README.md

(
echo @echo off
echo echo ========================================================
echo echo        Running %SOFT_TITLE%
echo echo ========================================================
echo pause
) > launch.bat

echo [*] Staging and committing files...
git add .
git commit -m "Initialize software branch: %BRANCH_NAME%"

echo.
set /p PUSH_NOW="Do you want to push this branch to GitHub now? (Y/N): "
if /i "%PUSH_NOW%"=="Y" (
    echo [*] Pushing branch %BRANCH_NAME% to GitHub...
    git push -u origin %BRANCH_NAME%
    echo.
    echo ========================================================
    echo [SUCCESS] Branch pushed to GitHub!
    echo The live website will automatically detect and show
    echo this new software without you editing index.html!
    echo ========================================================
) else (
    echo.
    echo [INFO] You can push it later with: git push -u origin %BRANCH_NAME%
)

echo.
echo [*] Switching back to main branch...
git checkout main

echo.
echo Done!
pause
