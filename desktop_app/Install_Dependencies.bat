@echo off
title Install Dependencies - Doctors For You HRMS
cd /d "%~dp0"

echo ===============================================================================
echo                Doctors For You - HR Operations Platform
echo                       Dependencies Installer
echo ===============================================================================
echo.
echo Installing all required packages from requirements.txt...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/2] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [2/2] Installing libraries (flet, python-docx, pandas, openpyxl, pywin32, etc.)...
python -m pip install -r "%~dp0requirements.txt"

if %errorlevel% neq 0 (
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
