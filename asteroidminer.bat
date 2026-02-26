@echo off
echo ========================================
echo    ASTEROID MINER LAUNCHER
echo ========================================
echo.

python launcher.py

if errorlevel 1 (
    echo.
    echo Error running the game!
    echo Make sure Python is installed and in your PATH.
    echo.
    pause
) else (
    echo.
    echo Game closed successfully.
)
