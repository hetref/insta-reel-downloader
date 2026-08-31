# Instagram Downloader API

A lightweight, high-performance FastAPI service to download Instagram Reels (Videos), Posts, and Image Carousels using `yt-dlp`. Exposed locally and securely tunneled to `https://reel-downloader-api.aryanshinde.in` via Cloudflare Tunnels.

---

## 🚀 Quick Start (Running Locally)

### 1. Start the FastAPI Server
```powershell
.\.venv\Scripts\python.exe main.py
```
*(Server runs locally on `http://127.0.0.1:8000`)*

### 2. Start the Cloudflare Tunnel
In a separate terminal window, launch the tunnel connected to `reel-downloader-api.aryanshinde.in`:
```powershell
cloudflared tunnel --config cloudflared_config.yml run reel-downloader-api
```

---

## 🌐 Public Domain & DNS Configuration

- **Public URL**: `https://reel-downloader-api.aryanshinde.in`
- **Tunnel ID**: `30b9788a-15f1-450c-bbcb-453cda622ebf`
- **DNS Record**:
  - **Type**: `CNAME`
  - **Name**: `reel-downloader-api`
  - **Target**: `30b9788a-15f1-450c-bbcb-453cda622ebf.cfargotunnel.com`
  - **Proxy Status**: Proxied (Orange Cloud)

---

## 📡 API Endpoints

### 1. Health Check
- **Endpoint**: `GET /health` or `GET https://reel-downloader-api.aryanshinde.in/health`
- **Response**:
  ```json
  {
    "status": "online",
    "message": "Instagram Downloader API is active"
  }
  ```

### 2. Download Media (Reel or Post)
- **Endpoint**: `POST /download` or `POST https://reel-downloader-api.aryanshinde.in/download`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "url": "https://www.instagram.com/reels/DcjIV1-K8e8/"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "status": "success",
    "download_urls": [
      "https://reel-downloader-api.aryanshinde.in/files/DcjIV1-K8e8_1.mp4"
    ]
  }
  ```

### 3. Stream / Fetch Downloaded Media File
- **Endpoint**: `GET https://reel-downloader-api.aryanshinde.in/files/<filename>`
- **Description**: Access or download the file directly via your browser or HTTP client.

### 4. Delete Downloaded File
- **Endpoint**: `POST /delete` or `POST https://reel-downloader-api.aryanshinde.in/delete`
- **Headers**: `Content-Type: application/json`
- **Request Body** (Pass the exact `file_url` received from `/download`):
  ```json
  {
    "file_url": "https://reel-downloader-api.aryanshinde.in/files/DcjIV1-K8e8_1.mp4"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "status": "success",
    "message": "File 'DcjIV1-K8e8_1.mp4' deleted successfully."
  }
  ```
