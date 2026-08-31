#!/bin/bash

# Navigate to script directory
cd "$(dirname "$0")"

echo "==================================================="
echo "  Starting Instagram Downloader FastAPI Server..."
echo "==================================================="

# Ensure downloads directory exists
mkdir -p downloads

# Activate virtual environment and launch FastAPI server in background
source .venv/bin/activate
python main.py &
FASTAPI_PID=$!

sleep 3

echo "==================================================="
echo "  Connecting Cloudflare Tunnel to:"
echo "  https://reel-downloader-api.aryanshinde.in"
echo "==================================================="
echo ""
echo "[INFO] API Base URL: https://reel-downloader-api.aryanshinde.in"
echo "[INFO] Files Route:  https://reel-downloader-api.aryanshinde.in/files/"
echo ""
echo "[INFO] Press Ctrl+C in this window to stop both server and tunnel."
echo ""

# Run Cloudflare Tunnel
cloudflared tunnel --config cloudflared_config.yml run reel-downloader-api

# Kill background FastAPI process when tunnel is stopped
kill $FASTAPI_PID 2>/dev/null
