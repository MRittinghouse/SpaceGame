@echo off
REM ============================================================
REM Space Trader Game Launcher for Windows
REM ============================================================

echo.
echo ============================================================
echo   SPACE TRADER - Game Launcher
echo   A Narrative-Driven Space Trading RPG
echo ============================================================
echo.

REM Check if virtual environment exists
if exist .venv\Scripts\python.exe (
    echo [INFO] Using virtual environment Python...
    echo.
    .venv\Scripts\python.exe run.py
) else (
    echo [WARNING] Virtual environment not found at .venv\
    echo [INFO] Using system Python...
    echo.
    python run.py
)

echo.
echo ============================================================
echo   Game Closed
echo ============================================================
echo.

REM Only pause if there was an error
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Game exited with error code: %ERRORLEVEL%
    pause
)
