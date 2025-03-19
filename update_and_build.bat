@echo off
setlocal enabledelayedexpansion

:: Store the current directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Starting build process...

:: Check if we're running with admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrative privileges.
    
    :: Re-run the script with admin privileges while preserving the working directory
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%SCRIPT_DIR%\" && %~nx0' -Verb RunAs"
    exit /b
)

:: Create a temporary Python environment if Python is not available
set PYTHON_URL=https://www.python.org/ftp/python/3.9.13/python-3.9.13-embed-amd64.zip
set TEMP_DIR=%~dp0temp
set PYTHON_ZIP=%TEMP_DIR%\python.zip
set PYTHON_DIR=%TEMP_DIR%\python

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: Download and extract Python if not present
if not exist "%PYTHON_DIR%" (
    echo Downloading temporary Python environment...
    powershell -Command "(New-Object Net.WebClient).DownloadFile('%PYTHON_URL%', '%PYTHON_ZIP%')"
    powershell -Command "Expand-Archive '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%'"
    del "%PYTHON_ZIP%"
)

:: Set Python path
set PATH=%PYTHON_DIR%;%PATH%

:: Check if required files exist
if not exist "main.py" (
    echo main.py not found
    pause
    exit /b 1
)

if not exist "oniplugin.spec" (
    echo oniplugin.spec not found
    pause
    exit /b 1
:: First uninstall pathlib if it exists
echo Checking for pathlib...
pip uninstall -y pathlib >nul 2>&1

:: Run the build with output to both console and log file
echo Building executable...
"%SCRIPT_DIR%\python" "%SCRIPT_DIR%\build.py" > "%SCRIPT_DIR%\logs\build_log.txt" 2>&1
if %ERRORLEVEL% neq 0 (
    echo Build failed! Check logs\build_log.txt for details
    type "%SCRIPT_DIR%\logs\build_log.txt"
) else (
    echo Build completed successfully!
    echo Executable can be found in the dist directory
)
    type logs\build_log.txt
) else (
    echo Build completed successfully!
    echo Executable can be found in the dist directory
)

pause

