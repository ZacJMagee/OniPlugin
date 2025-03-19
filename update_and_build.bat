@echo off
setlocal enabledelayedexpansion

:: Store the current directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Create logs directory if it doesn't exist
if not exist "%SCRIPT_DIR%\logs" mkdir "%SCRIPT_DIR%\logs"

echo Starting build process... > "%SCRIPT_DIR%\logs\build_log.txt"
echo %date% %time%: Script started >> "%SCRIPT_DIR%\logs\build_log.txt"

:: Check for required files
if not exist "main.py" (
    echo main.py not found
    echo %date% %time%: main.py not found >> "%SCRIPT_DIR%\logs\build_log.txt"
    pause
    exit /b 1
)

if not exist "oniplugin.spec" (
    echo oniplugin.spec not found
    echo %date% %time%: oniplugin.spec not found >> "%SCRIPT_DIR%\logs\build_log.txt"
    pause
    exit /b 1
)

:: Check if we're running with admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrative privileges.
    echo Requesting admin rights...
    echo %date% %time%: Requesting admin rights >> "%SCRIPT_DIR%\logs\build_log.txt"
    
    :: Re-run the script with admin privileges while preserving the working directory
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%SCRIPT_DIR%\" && call \"%~nx0\" && pause' -Verb RunAs" -WindowStyle Normal
    exit /b
)

:: Check if git is available
where git >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Updating from Git repository...
    echo %date% %time%: Attempting git pull >> "%SCRIPT_DIR%\logs\build_log.txt"
    
    :: Check if .git directory exists
    if exist ".git" (
        git pull >> "%SCRIPT_DIR%\logs\build_log.txt" 2>&1
        if %ERRORLEVEL% neq 0 (
            echo Git pull failed. Check logs\build_log.txt for details.
            echo %date% %time%: Git pull failed >> "%SCRIPT_DIR%\logs\build_log.txt"
        ) else (
            echo Successfully updated from Git.
            echo %date% %time%: Git pull successful >> "%SCRIPT_DIR%\logs\build_log.txt"
        )
    ) else (
        echo Not a git repository. Skipping update.
        echo %date% %time%: Not a git repository >> "%SCRIPT_DIR%\logs\build_log.txt"
    )
) else (
    echo Git not found. Skipping update.
    echo %date% %time%: Git not found >> "%SCRIPT_DIR%\logs\build_log.txt"
)

:: First uninstall pathlib if it exists
echo Checking for pathlib...
echo %date% %time%: Checking for pathlib >> "%SCRIPT_DIR%\logs\build_log.txt"
pip uninstall -y pathlib >nul 2>&1

:: Run the build with output to both console and log file
echo Building executable...
echo %date% %time%: Starting build process >> "%SCRIPT_DIR%\logs\build_log.txt"

python "%SCRIPT_DIR%\build.py" >> "%SCRIPT_DIR%\logs\build_log.txt" 2>&1
if %ERRORLEVEL% neq 0 (
    echo Build failed! Check logs\build_log.txt for details
    echo %date% %time%: Build failed with error code %ERRORLEVEL% >> "%SCRIPT_DIR%\logs\build_log.txt"
    type "%SCRIPT_DIR%\logs\build_log.txt"
) else (
    echo Build completed successfully!
    echo Executable can be found in the dist directory
    echo %date% %time%: Build completed successfully >> "%SCRIPT_DIR%\logs\build_log.txt"
)

echo.
echo Build process finished. Check logs\build_log.txt for details.
echo %date% %time%: Script completed >> "%SCRIPT_DIR%\logs\build_log.txt"
pause

