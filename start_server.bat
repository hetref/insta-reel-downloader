@echo off
TITLE Instagram Downloader API ^& Cloudflare Tunnel
echo ===================================================
echo   Starting Instagram Downloader FastAPI Server...
echo ===================================================

cd /d "%~dp0"

:: Ensure downloads directory exists
if not exist "downloads" mkdir downloads

:: Start FastAPI server in a separate background process
start "FastAPI Server" /min .\.venv\Scripts\python.exe main.py

echo Waiting for FastAPI server to initialize on http://127.0.0.1:8000 ...
timeout /t 3 /nobreak > nul

echo ===================================================
echo   Connecting Cloudflare Tunnel to:
echo   https://reel-downloader-api.aryanshinde.in
echo ===================================================
echo.
echo [INFO] API Base URL: https://reel-downloader-api.aryanshinde.in
echo [INFO] Files Route:  https://reel-downloader-api.aryanshinde.in/files/
echo.
echo [INFO] Press Ctrl+C in this window to stop the Tunnel ^& Server.
echo.

cloudflared tunnel --config cloudflared_config.yml run reel-downloader-api

echo.
echo Stopping FastAPI Server...
taskkill /FI "WINDOWTITLE eq FastAPI Server*" /F > nul 2>&1
echo Done.
pause
