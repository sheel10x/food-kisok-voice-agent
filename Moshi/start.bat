@echo off
title Moshi — Full-Duplex Voice AI
color 0B

cd /d "%~dp0"

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║   🎙️  MOSHI — Full-Duplex Voice AI              ║
echo  ║   arXiv: 2410.00037  ^|  Kyutai Labs             ║
echo  ╠═══════════════════════════════════════════════════╣
echo  ║   Open: http://localhost:8998                    ║
echo  ║   Press Ctrl+C to stop                           ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

:: Open browser after short delay (background)
start /b "" timeout /t 3 /nobreak >nul && start "" "http://localhost:8998"

:: Start server
python app.py

echo.
echo  Server stopped.
pause
