@echo off
title Space Trader
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m spacegame.main
) else (
    echo Virtual environment not found. Please run install.bat first.
    pause
)
