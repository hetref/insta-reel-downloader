# Beginner's Guide: Running FastAPI & Exposing via Cloudflare Tunnel

This guide walks new users step-by-step through setting up, running the FastAPI Instagram Downloader server on a local machine, exposing it to a custom domain (`https://reel-downloader-api.aryanshinde.in`) using Cloudflare Tunnels, and making API requests.

---

## Table of Contents
1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Step 1: Start the Local FastAPI Server](#step-1-start-the-local-fastapi-server)
4. [Step 2: Connect & Run Cloudflare Tunnel](#step-2-connect--run-cloudflare-tunnel)
5. [Step 3: DNS Record Setup in Cloudflare](#step-3-dns-record-setup-in-cloudflare)
6. [Step 4: Making Requests to the Public API](#step-4-making-requests-to-the-public-api)
   - [Health Check Endpoint](#health-check-endpoint)
   - [Download Endpoint (Reels & Image Posts)](#download-endpoint-reels--image-posts)
   - [Fetching File Directly](#fetching-file-directly)
   - [Delete Endpoint](#delete-endpoint)
7. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## 1. Overview

```
 [ Client / Frontend Request ]
               │
               ▼
   https://reel-downloader-api.aryanshinde.in
               │
               ▼
    [ Cloudflare Edge Network ]
               │
               ▼ (Secure Tunnel Connection)
    [ cloudflared daemon on Laptop ]
               │
               ▼
    [ Local FastAPI Server: http://127.0.0.1:8000 ]
               │
               ├──────► /download -> Returns file URL: https://reel-downloader-api.aryanshinde.in/files/filename.mp4
               ├──────► /files/filename.mp4 -> Serves raw file via HTTP GET
               └──────► /delete -> Deletes file from downloads/ directory
```

---

## 2. Prerequisites

1. **Python 3.10+**: Installed on your laptop.
2. **`cloudflared` CLI**: Installed on your system (`winget install Cloudflare.cloudflared` on Windows or `brew install cloudflared` on macOS).
3. **Instagram Cookie Session**: Logged into Instagram on Chrome (or a `cookies.txt` file in the project folder).

---

## Step 1: Start the Local FastAPI Server

Open your terminal or PowerShell inside the project directory (`reel-downloader/`):

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start the FastAPI Uvicorn server
python main.py
```

---

## Step 2: Connect & Run Cloudflare Tunnel

Open a **second terminal window** in the same project directory and run the configured Cloudflare tunnel:

```powershell
cloudflared tunnel --config cloudflared_config.yml run reel-downloader-api
```

Your local server is now securely live at: `https://reel-downloader-api.aryanshinde.in`

---

## Step 3: DNS Record Setup in Cloudflare

Verify or add the DNS record in your Cloudflare Dashboard:

| Type | Name | Target / Content | Proxy Status |
|---|---|---|---|
| **CNAME** | `reel-downloader-api` | `30b9788a-15f1-450c-bbcb-453cda622ebf.cfargotunnel.com` | **Proxied** (Orange Cloud) |

---

## Step 4: Making Requests to the Public API

### Health Check Endpoint
- **URL**: `GET https://reel-downloader-api.aryanshinde.in/health`
- **cURL Command**:
  ```bash
  curl -X GET "https://reel-downloader-api.aryanshinde.in/health"
  ```
- **Response**:
  ```json
  {
    "status": "online",
    "message": "Instagram Downloader API is active"
  }
  ```

---

### Download Endpoint (Reels & Image Posts)
- **URL**: `POST https://reel-downloader-api.aryanshinde.in/download`
- **Header**: `Content-Type: application/json`

#### Example Request:
```bash
curl -X POST "https://reel-downloader-api.aryanshinde.in/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reels/DcjIV1-K8e8/"}'
```
- **Response**:
  ```json
  {
    "status": "success",
    "download_urls": [
      "https://reel-downloader-api.aryanshinde.in/files/DcjIV1-K8e8_1.mp4"
    ]
  }
  ```

---

### Fetching File Directly
You can open or fetch the downloaded file directly using the URL returned in `download_urls`:
```bash
curl -O "https://reel-downloader-api.aryanshinde.in/files/DcjIV1-K8e8_1.mp4"
```

---

### Delete Endpoint
- **URL**: `POST https://reel-downloader-api.aryanshinde.in/delete`
- **Header**: `Content-Type: application/json`

Pass the exact `file_url` returned from `/download`:
```bash
curl -X POST "https://reel-downloader-api.aryanshinde.in/delete" \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://reel-downloader-api.aryanshinde.in/files/DcjIV1-K8e8_1.mp4"}'
```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "File 'DcjIV1-K8e8_1.mp4' deleted successfully."
  }
  ```

---

## Troubleshooting & FAQ

### Q: What if I get an Instagram login / 401 error?
**A**: Ensure Chrome is logged in to Instagram on your computer, or place an updated `cookies.txt` file into the `reel-downloader/` project root directory.
