@echo off
setlocal EnableDelayedExpansion
title Doctors For You - HR Operations Platform
cd /d "%~dp0"

:: Check for non-interactive flag across arguments
for %%A in (%*) do (
    if /i "%%~A"=="--no-pause" set "NON_INTERACTIVE=1"
)

:: Check for command line flags
if /i "%~1"=="--create-shortcut" goto :create_shortcut
if /i "%~1"=="/create-shortcut"  goto :create_shortcut
if /i "%~1"=="--shortcut"         goto :create_shortcut
if /i "%~1"=="/shortcut"          goto :create_shortcut
if /i "%~1"=="-s"                 goto :create_shortcut
if /i "%~1"=="--help"             goto :show_help
if /i "%~1"=="-h"                 goto :show_help
if /i "%~1"=="/?"                 goto :show_help
if /i "%~1"=="--check-env"        goto :check_env_only
if /i "%~1"=="--dry-run"          goto :check_env_only

echo ===============================================================================
echo                Doctors For You - HR Operations Platform
echo                       Desktop Application Launcher
echo ===============================================================================
echo.

:: 1. Probe for Python environment in order:
set "PYTHON_EXE="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [OK] Using virtual environment .venv
    goto :python_found
)

if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    echo [OK] Using virtual environment venv
    goto :python_found
)

python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    echo [OK] Using system Python from PATH
    goto :python_found
)

py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py"
    echo [OK] Using Windows Python Launcher py
    goto :python_found
)

:python_found
if "%PYTHON_EXE%"=="" (
    echo ===============================================================================
    echo [ERROR] Python was not found on your system!
    echo ===============================================================================
    echo.
    echo The DFY HRMS Platform requires Python 3.10 or higher.
    echo.
    echo What you can do:
    echo 1. Install Python from https://www.python.org/downloads/
    echo 2. During installation, make sure to check "Add python.exe to PATH"
    echo 3. Or create a virtual environment in .venv or venv folder.
    echo.
    echo If you need assistance, please contact the IT/HR technical team.
    echo ===============================================================================
    echo.
    if not defined NON_INTERACTIVE pause
    exit /b 1
)

:: 2. Configure environment variables
set "PYTHONPATH=%~dp0desktop_app;%~dp0;%PYTHONPATH%"

:: 3. Launch Desktop Application
echo [INFO] Launching Doctors For You HR Operations Platform...
echo.
"%PYTHON_EXE%" "%~dp0desktop_app\main.py" %*
set "APP_EXIT_CODE=%errorlevel%"

if %APP_EXIT_CODE% neq 0 (
    echo.
    echo ===============================================================================
    echo [ERROR] Application encountered an error or terminated unexpectedly.
    echo Exit Code: %APP_EXIT_CODE%
    echo Please review any messages above or check the logs directory.
    echo ===============================================================================
    echo.
    if not defined NON_INTERACTIVE pause
    exit /b %APP_EXIT_CODE%
)

exit /b 0

:: ===============================================================================
:: Check Environment Mode (for automated testing / verification)
:: ===============================================================================
:check_env_only
set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [OK] Found .venv Python: "!PYTHON_EXE!"
    goto :env_check_done
)
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    echo [OK] Found venv Python: "!PYTHON_EXE!"
    goto :env_check_done
)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    echo [OK] Found system Python in PATH
    goto :env_check_done
)
py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py"
    echo [OK] Found Windows Python Launcher py
    goto :env_check_done
)

:env_check_done
if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found
    exit /b 1
)

echo [SUCCESS] Environment check passed. Python: "%PYTHON_EXE%"
exit /b 0

:: ===============================================================================
:: Create Desktop Shortcut Routine
:: ===============================================================================
:create_shortcut
echo ===============================================================================
echo           Doctors For You - Desktop Shortcut Creator Helper
echo ===============================================================================
echo.
echo Creating shortcut on your Windows Desktop...

set "VBS_TEMP=%TEMP%\dfy_shortcut_temp.vbs"
> "%VBS_TEMP%" echo Set ws = CreateObject("WScript.Shell"^)
>> "%VBS_TEMP%" echo sDesk = ws.SpecialFolders("Desktop"^)
>> "%VBS_TEMP%" echo Set link = ws.CreateShortcut(sDesk ^& "\DFY HR Operations Platform.lnk"^)
>> "%VBS_TEMP%" echo link.TargetPath = "%~dp0Launch_DFY_HRMS.bat"
>> "%VBS_TEMP%" echo link.WorkingDirectory = "%~dp0"
>> "%VBS_TEMP%" echo link.Description = "Doctors For You - HR Operations Platform"
>> "%VBS_TEMP%" echo link.Save

cscript //nologo "%VBS_TEMP%"
set "VBS_RESULT=%errorlevel%"
if exist "%VBS_TEMP%" del "%VBS_TEMP%" >nul 2>&1

if %VBS_RESULT% equ 0 goto :shortcut_success
echo.
echo [ERROR] Failed to create Desktop shortcut (Code: %VBS_RESULT%).
echo.
goto :shortcut_finish

:shortcut_success
echo.
echo [SUCCESS] Desktop shortcut "DFY HR Operations Platform" has been created!
echo You can now launch the application directly from your Windows Desktop.
echo.

:shortcut_finish
if not defined NON_INTERACTIVE pause
exit /b %VBS_RESULT%

:: ===============================================================================
:: Help Information
:: ===============================================================================
:show_help
echo ===============================================================================
echo            Doctors For You - HR Operations Platform Launcher
echo ===============================================================================
echo.
echo Usage:
echo   Launch_DFY_HRMS.bat                      Launch the DFY HRMS Desktop Application
echo   Launch_DFY_HRMS.bat --create-shortcut    Create a 1-Click shortcut on your Desktop
echo   Launch_DFY_HRMS.bat --check-env          Verify the Python environment without GUI
echo   Launch_DFY_HRMS.bat --help               Show this help information
echo.
exit /b 0
