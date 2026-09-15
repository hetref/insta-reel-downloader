# Linux Server Management Guide

This document contains all commands and workflows for managing the **Instagram Downloader FastAPI Server** (`reel-downloader.service`) and the **Caddy Reverse Proxy** (`n8n-docker-caddy-caddy-1`) on your Linux server.

---

## 📋 Table of Contents
1. [FastAPI Service Commands (systemctl)](#1-fastapi-service-commands-systemctl)
2. [Viewing Real-Time Logs](#2-viewing-real-time-logs)
3. [Updating Code & Restarting](#3-updating-code--restarting-workflow)
4. [Caddy Reverse Proxy Management](#4-caddy-reverse-proxy-management)
5. [Health Checks & Troubleshooting](#5-health-checks--troubleshooting)
6. [API Secret Key Authentication (.env)](#6-api-secret-key-authentication-env)
7. [Automated 30-Minute Cleanup Cron Job](#7-automated-30-minute-cleanup-cron-job)
8. [Quick Reference Cheat Sheet](#8-quick-reference-cheat-sheet)

---

## 1. FastAPI Service Commands (`systemctl`)

The API runs as a systemd background service named `reel-downloader.service`.

### Check Service Status
```bash
sudo systemctl status reel-downloader
```

### Restart Service
Use this whenever you change code, environment variables, or dependencies:
```bash
sudo systemctl restart reel-downloader
```

### Start Service
```bash
sudo systemctl start reel-downloader
```

### Stop Service
```bash
sudo systemctl stop reel-downloader
```

### Enable Auto-Start on Boot
```bash
sudo systemctl enable reel-downloader
```

### Disable Auto-Start on Boot
```bash
sudo systemctl disable reel-downloader
```

### Reload systemd Daemon (After editing `.service` file)
If you ever edit `/etc/systemd/system/reel-downloader.service`, always reload before restarting:
```bash
sudo systemctl daemon-reload
sudo systemctl restart reel-downloader
```

---

## 2. Viewing Real-Time Logs

### Stream API Logs in Real-Time (Follow Mode)
This streams every incoming request (`/download`, `/health`, errors) live:
```bash
journalctl -u reel-downloader -f
```
*(Press `Ctrl + C` at any time to exit).*

### View Recent 50 Lines & Follow
```bash
journalctl -u reel-downloader -f -n 50
```

### View Only Errors
```bash
journalctl -u reel-downloader -p err -e
```

---

## 3. Updating Code & Restarting (Workflow)

When you make changes locally, push to Git, and want to apply them on the server:

```bash
# 1. Navigate to the project directory
cd /root/projects/insta-reel-downloader

# 2. Pull latest code from GitHub / Git
git pull

# 3. (Optional) Install newly added dependencies if requirements.txt changed
source .venv/bin/activate
pip install -r requirements.txt

# 4. Restart the FastAPI service
sudo systemctl restart reel-downloader

# 5. Verify the service is active and running
sudo systemctl status reel-downloader
```

---

## 4. Caddy Reverse Proxy Management

Caddy runs inside Docker as part of the `n8n-docker-caddy` stack, managing SSL certificates and routing traffic from `https://reel-download-api-cloud.aryanshinde.in` to internal port `8000`.

- **Caddyfile Path on Host**: `/opt/n8n-docker-caddy/caddy_config/Caddyfile`

### Reload Caddy (Zero Downtime)
Use this after editing the `Caddyfile` so changes apply immediately without dropping connections to n8n or your API:
```bash
docker exec -w /etc/caddy n8n-docker-caddy-caddy-1 caddy reload
```

### View Real-Time Caddy Logs
Watch incoming HTTPS connections, SSL status, and proxy activity:
```bash
docker logs -f n8n-docker-caddy-caddy-1
```
*(Press `Ctrl + C` to exit).*

### View the Last 30 Caddy Logs
```bash
docker logs --tail 30 n8n-docker-caddy-caddy-1
```

### Restart Caddy Container (If needed)
```bash
docker restart n8n-docker-caddy-caddy-1
```

### Check Caddy Container Status
```bash
docker ps --filter "name=caddy"
```

---

## 5. Health Checks & Troubleshooting

### Test Server Locally (Bypassing Caddy & Domain)
```bash
curl http://127.0.0.1:8000/health
```
*Expected Output:*
```json
{"status":"online","message":"Instagram Downloader API is active"}
```

### Test Public Domain via HTTPS
```bash
curl -i https://reel-download-api-cloud.aryanshinde.in/health
```
*Expected Output:*
```text
HTTP/2 200 
...
{"status":"online","message":"Instagram Downloader API is active"}
```

### Test Download Endpoint
```bash
curl -X POST "https://reel-download-api-cloud.aryanshinde.in/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.instagram.com/reels/DcjIV1-K8e8/"}'
```

### Check if Port 8000 is Open & Listening
```bash
sudo ss -tulpn | grep 8000
```

### If you ever get `502 Bad Gateway` (Firewall Rule check)
Ensure Docker subnets are permitted to reach port 8000:
```bash
sudo iptables -I INPUT 1 -s 172.16.0.0/12 -p tcp --dport 8000 -j ACCEPT
```

---

## 6. API Secret Key Authentication (.env)

The API supports securing all endpoints with a secret key stored in your `.env` file or environment.

### Setting the Secret Key
On your Linux server in `/root/projects/insta-reel-downloader`:
```bash
nano .env
```
Add your secret:
```env
API_SECRET_KEY=my_ultra_secure_secret_key_12345
```
Then restart the service:
```bash
sudo systemctl restart reel-downloader
```

### Making Authorized Requests
Include `X-API-Key` or `X-API-Secret` in the headers of **every** request:

#### 1. Health Check
```bash
curl -i https://reel-download-api-cloud.aryanshinde.in/health \
     -H "X-API-Key: my_ultra_secure_secret_key_12345"
```

#### 2. Download Media
```bash
curl -X POST "https://reel-download-api-cloud.aryanshinde.in/download" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: my_ultra_secure_secret_key_12345" \
     -d '{"url": "https://www.instagram.com/reels/DcjIV1-K8e8/"}'
```

#### 3. Access Downloaded File (`/files/`)
Via header:
```bash
curl -O "https://reel-download-api-cloud.aryanshinde.in/files/DcjIV1-K8e8_1.mp4" \
     -H "X-API-Key: my_ultra_secure_secret_key_12345"
```
Or via query parameter (convenient for browser downloads):
```text
https://reel-download-api-cloud.aryanshinde.in/files/DcjIV1-K8e8_1.mp4?key=my_ultra_secure_secret_key_12345
```

- If the key is missing or wrong: Returns `401 Unauthorized`.
- If `API_SECRET_KEY` is not set in `.env`: The API remains open without authentication.

---

## 7. Automatic Continuous 30-Minute File Cleanup

### How it Works (100% Automatic — No Cron or Manual Steps Needed)
The FastAPI server has a **built-in background cleanup worker** running continuously 24/7.
- Every **60 seconds**, the background worker scans `downloads/`.
- If any file's age exceeds **30 minutes**, it is **deleted automatically**.
- As long as `reel-downloader.service` is running, cleanup happens continuously without you needing to run any command or set up cron!

You will see automatic cleanup logs in real-time when streaming server logs:
```bash
journalctl -u reel-downloader -f
```
*Live log example:*
```text
🗑️  [AUTO-CLEANUP] Deleted expired file: DcjIV1-K8e8_1.mp4 (Age: 30.2m, Size: 4120.5KB)
```

---

## 8. Quick Reference Cheat Sheet

| Action | Command |
|---|---|
| **Restart API** | `sudo systemctl restart reel-downloader` |
| **Check API Status** | `sudo systemctl status reel-downloader` |
| **Watch API Logs (Includes Auto-Cleanup)** | `journalctl -u reel-downloader -f` |
| **Reload Caddy** | `docker exec -w /etc/caddy n8n-docker-caddy-caddy-1 caddy reload` |
| **Watch Caddy Logs** | `docker logs -f n8n-docker-caddy-caddy-1` |
| **Restart Caddy** | `docker restart n8n-docker-caddy-caddy-1` |
| **Pull & Update App** | `git pull && sudo systemctl restart reel-downloader` |
