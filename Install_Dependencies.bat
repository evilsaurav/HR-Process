@echo off
setlocal EnableDelayedExpansion
title Install Dependencies - Doctors For You HRMS
cd /d "%~dp0"

echo ===============================================================================
echo                Doctors For You - HR Operations Platform
echo                       Dependencies Installer
echo ===============================================================================
echo.

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

if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
    echo [OK] Using parent virtual environment .venv
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
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo During installation, be sure to check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo.
echo Installing all required packages from requirements.txt...
echo.

"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt"

if !errorlevel! neq 0 (
    echo.
    echo ===============================================================================
    echo [ERROR] Package installation failed. Please check your internet connection.
    echo ===============================================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo [SUCCESS] All dependencies have been installed successfully!
echo You can now double-click "Launch_DFY_HRMS.bat" to start the application.
echo ===============================================================================
echo.
pause
exit /b 0
