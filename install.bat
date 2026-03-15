@echo off
title Space Trader - Installer
echo.
echo  =====================================================
echo       SPACE TRADER - Automated Installer
echo       A Narrative-Driven Space Trading RPG
echo  =====================================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.13+ from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [i] Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)
echo.

:: Activate venv and install dependencies
echo [i] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -e . --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

echo  =====================================================
echo   Installation complete!
echo.
echo   To play, double-click: play.bat
echo   Or run: .venv\Scripts\python.exe -m spacegame.main
echo  =====================================================
echo.
pause
