@echo off
setlocal enabledelayedexpansion

:: Enable command echoing for debugging
echo on

:: Store the current directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Create logs directory if it doesn't exist
if not exist "%SCRIPT_DIR%\logs" mkdir "%SCRIPT_DIR%\logs"

:: Try to create/append to log file with exclusive access
(
  echo Starting build process...
  echo %date% %time%: Script started
) > "%SCRIPT_DIR%\logs\build_log.txt" 2>nul || (
  echo Warning: Could not write to log file. It may be in use.
)

:: Debug point 1
echo Debug: Current directory is %CD% >> "%SCRIPT_DIR%\logs\build_log.txt"
echo Debug: Script directory is %SCRIPT_DIR% >> "%SCRIPT_DIR%\logs\build_log.txt"

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

:: Debug point 2
echo Debug: Required files found >> "%SCRIPT_DIR%\logs\build_log.txt"

:: Check if we're running with admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrative privileges.
    echo Requesting admin rights...
    echo %date% %time%: Requesting admin rights >> "%SCRIPT_DIR%\logs\build_log.txt"
    
    :: Debug point 3
    echo Debug: About to elevate privileges >> "%SCRIPT_DIR%\logs\build_log.txt"
    
    :: Close the log file before elevation to prevent access issues
    echo Debug: Preparing for elevation >> "%SCRIPT_DIR%\logs\build_log.txt"
    
    :: Use PowerShell to elevate and run the script directly
    powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command ""cd ''%SCRIPT_DIR%''; & ''%~f0''""' -Verb RunAs -Wait -WindowStyle Normal"
    exit /b
Replace lines: 0-0
```dosbatch
)

:: Debug point 4 - If we get here, we have admin rights
echo Debug: Admin privileges confirmed >> "%SCRIPT_DIR%\logs\build_log.txt"

:: Debug point 5 - Starting main execution
echo %date% %time%: Admin check passed, continuing with build... >> "%SCRIPT_DIR%\logs\build_log.txt"
echo Admin check passed, continuing with build...
echo Debug: Starting main execution >> "%SCRIPT_DIR%\logs\build_log.txt"

:: Add a small delay to ensure log file is written
timeout /t 2 >nul

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

python "%SCRIPT_DIR%\build.py"
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

