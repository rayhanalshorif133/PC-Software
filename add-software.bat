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

echo.
echo [*] Creating orphan branch: %BRANCH_NAME% ...
git checkout --orphan %BRANCH_NAME%

echo [*] Cleaning staging area for fresh software files...
git rm -rf . >nul 2>&1

echo.
echo [*] Creating placeholder files for %BRANCH_NAME% ...
echo # %BRANCH_NAME% > README.md
echo. >> README.md
echo Put your software files, installation scripts, or portable binaries here. >> README.md
echo. >> README.md
echo ### How to clone this branch directly: >> README.md
echo ```bash >> README.md
echo git clone -b %BRANCH_NAME% --single-branch https://github.com/rayhanalshorif133/PC-Software.git >> README.md
echo ``` >> README.md

echo @echo off > run-software.bat
echo echo Running %BRANCH_NAME% ... >> run-software.bat
echo pause >> run-software.bat

echo [*] Staging and committing files...
git add .
git commit -m "Initialize software branch: %BRANCH_NAME%"

echo.
echo ========================================================
echo [SUCCESS] Branch %BRANCH_NAME% created!
echo.
echo Now you can:
echo 1. Put your software files into this folder.
echo 2. Run: git add .
echo 3. Run: git commit -m "Add files for %BRANCH_NAME%"
echo 4. Run: git push -u origin %BRANCH_NAME%
echo 5. Switch back to website: git checkout main
echo ========================================================
pause
