# Instagram Media Downloader & API

An autonomous Python-based solution for downloading Instagram **Reels (Videos)**, **Single Posts**, and **Multi-Image Carousel Posts** using `yt-dlp` and Chrome browser authentication cookies. It features both a standalone script (`ig_downloader.py`) and a lightweight, high-performance REST API built with **FastAPI** (`main.py`).

---

## Table of Contents
1. [Why This Was Built](#why-this-was-built)
2. [Project Architecture & Key Logic](#project-architecture--key-logic)
3. [Features](#features)
4. [Prerequisites & Setup](#prerequisites--setup)
5. [Standalone Downloader Script (`ig_downloader.py`)](#standalone-downloader-script-ig_downloaderpy)
6. [FastAPI REST Service (`main.py`)](#fastapi-rest-service-mainpy)
   - [Running the Server](#running-the-server)
   - [API Endpoints](#api-endpoints)
7. [Bypassing Instagram Rate Limits & Login Walls](#bypassing-instagram-rate-limits--login-walls)
8. [File Structure](#file-structure)

---

## Why This Was Built

Instagram actively blocks anonymous media extraction using strict rate-limiting, IP reputation checks, and login redirect walls (HTTP 401 / redirect to login page). Traditional scrapers (like deprecated `youtube-dl` or older `instaloader` forks) are frequently blocked or broken by Instagram's dynamic frontend updates.

This project was built to address these challenges by providing:
1. **Cookie-Based Authentication Bypass**: Utilizes local browser session cookies (`chrome`) via `yt-dlp` to present authenticated requests to Instagram.
2. **Unified Media Extraction**: Extracts both video formats (`.mp4`) for Reels/videos and high-resolution thumbnail images (`.jpg`) for image/carousel posts.
3. **REST API Interface**: Exposes download and cleanup endpoints so external services or frontend applications can consume Instagram downloads without cluttering local disk storage.

---

## Project Architecture & Key Logic

```
   [ Client / API Request ]
             │
             ▼
   ┌───────────────────┐
   │  FastAPI Router   │ (/download or /delete)
   └─────────┬─────────┘
             │
             ▼
   ┌───────────────────┐
   │   yt-dlp Engine   │ (Configured with 'cookiesfrombrowser': ('chrome',))
   └─────────┬─────────┘
             │
      ┌──────┴────────────────────────┐
      ▼                               ▼
[ Video Media ]               [ Image / Carousel ]
yt-dlp extracts video          Direct HTTP fetch of highest-
streams to downloads/*.mp4     resolution image to downloads/*.jpg
```

### How Media Extraction Works:
1. **Metadata Inspection**: `extract_info(url, download=False, process=False)` is executed to fetch the post schema without automatically triggering a video stream error for non-video image posts.
2. **Format Distinction**:
   - **Video/Reel Posts**: Checked for valid video formats (`vcodec != 'none'`). If present, `yt-dlp` processes and streams the video directly into the `downloads/` directory.
   - **Image/Carousel Posts**: Instagram image posts do not contain video streams. The script identifies the entries array (for carousels) or single entry and downloads the highest-resolution thumbnail image directly via HTTP request headers (`User-Agent: Mozilla/5.0`).
3. **Path Tracking & Cleanup**: Every saved item yields a clean local path relative to the project root (e.g., `downloads/DcjIV1-K8e8_1.mp4`). The `/delete` endpoint validates path safety before removing the file.

---

## Features

- **Reel & Video Downloader**: Downloads high-definition `.mp4` video files.
- **Image & Carousel Downloader**: Extracts all images from single and multi-item carousel posts (`.jpg`).
- **Browser Cookie Integration**: Uses active Chrome session cookies to bypass Instagram login walls.
- **RESTful API**: Fast, asynchronous endpoints built on **FastAPI** & **Uvicorn**.
- **Safe Delete Endpoint**: Prevents directory traversal attacks by enforcing path containment inside the `downloads/` directory.

---

## Prerequisites & Setup

### Requirements
- Python 3.10+
- Google Chrome browser (logged into Instagram)
- Operating System: Windows, macOS, or Linux

### Setup Instructions
1. **Clone or navigate into the repository**:
   ```cmd
   cd reel-downloader
   ```

2. **Create and activate virtual environment**:
   ```cmd
   python -m venv .venv
   .\.venv\Scripts\activate   # Windows
   # source .venv/bin/activate # Linux/macOS
   ```

3. **Install Dependencies**:
   ```cmd
   pip install yt-dlp fastapi uvicorn requests
   ```

---

## Standalone Downloader Script (`ig_downloader.py`)

The script `ig_downloader.py` can be executed directly from the terminal for testing or batch operations.

### Running the Script:
```cmd
.\.venv\Scripts\python.exe ig_downloader.py
```

### Code Walkthrough (`ig_downloader.py`):
```python
import os
import urllib.request
import yt_dlp

TEST_URLS = [
    "https://www.instagram.com/reels/DcjIV1-K8e8/",
    "https://www.instagram.com/p/DcgOltHCKgf/?img_index=2"
]

ydl_opts = {
    'format': 'best',
    'outtmpl': 'downloads/%(id)s_%(playlist_index|1)s.%(ext)s',
    'cookiesfrombrowser': ('chrome',),
    'ignoreerrors': True,
    'quiet': True,
}

def download_instagram_media(urls, opts):
    os.makedirs("downloads", exist_ok=True)
    if isinstance(urls, str):
        urls = [urls]
        
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            info = ydl.extract_info(url, download=False, process=False)
            if not info:
                continue
            
            entries = info.get('entries') if info.get('_type') == 'playlist' else [info]
            
            for idx, entry in enumerate(entries, start=1):
                if not entry:
                    continue
                
                has_video = False
                if entry.get('formats'):
                    has_video = any(f.get('vcodec') != 'none' for f in entry['formats'])
                
                entry_id = entry.get('id', f'item_{idx}')
                
                if has_video:
                    ydl.process_ie_result(entry, download=True)
                elif entry.get('thumbnails'):
                    best_thumbnail = entry['thumbnails'][-1]['url']
                    file_path = os.path.join("downloads", f"{entry_id}_{idx}.jpg")
                    req = urllib.request.Request(best_thumbnail, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
                        out_file.write(response.read())
```

---

## FastAPI REST Service (`main.py`)

### Running the Server
To start the production/development web server:
```cmd
.\.venv\Scripts\python.exe main.py
```
Or using Uvicorn CLI directly:
```cmd
uvicorn main:app --reload --port 8000
```
API Documentation (Swagger UI) is automatically available at:
`http://127.0.0.1:8000/docs`

---

### API Endpoints

#### 1. Download Media
- **Endpoint**: `POST /download`
- **Description**: Accepts an Instagram URL (Reel, Post, Image, or Carousel) and returns an array of relative file paths of the downloaded media files.
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
    "downloaded_files": [
      "downloads\\DcjIV1-K8e8_1.mp4"
    ]
  }
  ```

#### 2. Delete Media File
- **Endpoint**: `POST /delete`
- **Description**: Accepts a file path and deletes the file from disk to prevent storage buildup.
- **Request Body**:
  ```json
  {
    "file_path": "downloads\\DcjIV1-K8e8_1.mp4"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "status": "success",
    "message": "File 'downloads\\DcjIV1-K8e8_1.mp4' deleted successfully."
  }
  ```

---

## Bypassing Instagram Rate Limits & Login Walls

Instagram blocks anonymous scraper IP addresses. To ensure continuous operation:
1. Open Google Chrome on the host machine and log in to Instagram.
2. Keep `cookiesfrombrowser: ('chrome',)` enabled in `ydl_opts`.
3. If Chrome windows are locked or using a different browser, update `'chrome'` to `'firefox'`, `'edge'`, or `'safari'` in `ig_downloader.py` and `main.py`.

---

## File Structure

```
reel-downloader/
├── .venv/               # Python virtual environment
├── downloads/           # Output directory for downloaded videos and images
├── ig_downloader.py     # Standalone Python downloader script
├── main.py              # FastAPI application server with /download and /delete endpoints
└── README.md            # Comprehensive project documentation
```
