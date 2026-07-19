@echo off
title Moshi — Installing Dependencies
color 0B

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║   🎙️  MOSHI Full-Duplex Voice AI               ║
echo  ║   Installing dependencies...                     ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/4] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [2/4] Installing core server packages...
pip install fastapi==0.115.0 uvicorn[standard]==0.30.6 numpy==1.26.4 --quiet

echo [3/4] Installing voice AI packages...
pip install edge-tts==6.1.12 SpeechRecognition==3.10.4 scipy==1.13.1 --quiet

echo [4/4] Installing utilities...
pip install aiofiles==23.2.1 python-multipart==0.0.9 --quiet

echo.
echo  ✅ Installation complete!
echo  Run start.bat to launch Moshi
echo.
pause
