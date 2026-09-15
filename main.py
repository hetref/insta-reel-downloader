import asyncio
import os
import time
import urllib.request
from contextlib import asynccontextmanager
import yt_dlp
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Automatically load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Built-in fallback parser if python-dotenv is not yet installed
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
FILE_RETENTION_SECONDS = int(os.environ.get("FILE_RETENTION_MINUTES", 30)) * 60

async def continuous_cleanup_worker():
    """Continuously runs in the background. Deletes any file older than 30 minutes."""
    while True:
        try:
            now = time.time()
            cutoff = now - FILE_RETENTION_SECONDS
            if os.path.exists(DOWNLOADS_DIR):
                for filename in os.listdir(DOWNLOADS_DIR):
                    filepath = os.path.join(DOWNLOADS_DIR, filename)
                    if os.path.isfile(filepath) and not filename.startswith("."):
                        try:
                            file_mtime = os.path.getmtime(filepath)
                            if file_mtime < cutoff:
                                file_size = os.path.getsize(filepath)
                                age_min = round((now - file_mtime) / 60, 1)
                                os.remove(filepath)
                                size_kb = round(file_size / 1024, 1)
                                print(f"🗑️  [AUTO-CLEANUP] Deleted expired file: {filename} (Age: {age_min}m, Size: {size_kb}KB)", flush=True)
                        except Exception as e:
                            print(f"⚠️  [AUTO-CLEANUP ERROR] Failed to delete {filename}: {e}", flush=True)
        except Exception as e:
            print(f"⚠️  [AUTO-CLEANUP ERROR] Worker error: {e}", flush=True)
        
        # Check every 60 seconds
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start continuous background cleanup worker when server starts
    cleanup_task = asyncio.create_task(continuous_cleanup_worker())
    print(f"🕒 [STARTUP] Auto-cleanup background worker running (deletes files after {FILE_RETENTION_SECONDS // 60} minutes)", flush=True)
    yield
    cleanup_task.cancel()

app = FastAPI(
    title="Instagram Downloader API",
    description="API to download Instagram Reels, Posts, and Carousels and manage files locally.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def verify_api_secret(request: Request, call_next):
    # Retrieve secret from environment variable (.env or systemd)
    api_secret = os.environ.get("API_SECRET_KEY", "").strip()
    
    # If API_SECRET_KEY is configured, protect ALL endpoints (health, download, delete, files)
    if api_secret and request.url.path != "/favicon.ico":
        # Check header (X-API-Key or X-API-Secret) or query param (?api_key= or ?key=)
        provided_secret = (
            request.headers.get("x-api-key")
            or request.headers.get("x-api-secret")
            or request.query_params.get("api_key")
            or request.query_params.get("key")
        )
        if not provided_secret or provided_secret != api_secret:
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "message": "Unauthorized: Invalid or missing API secret key in 'X-API-Key' / 'X-API-Secret' header."
                }
            )
    return await call_next(request)

# Mount /files static route to serve downloaded media directly
app.mount("/files", StaticFiles(directory=DOWNLOADS_DIR), name="files")

COOKIE_FILE = os.path.abspath("cookies.txt")

class DownloadRequest(BaseModel):
    url: str

class DeleteRequest(BaseModel):
    file_url: str

def get_ydl_options():
    opts = {
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOADS_DIR, '%(id)s_%(playlist_index|1)s.%(ext)s'),
        'ignoreerrors': True,
        'no_warnings': True,
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    cookie_path = os.environ.get("IG_COOKIE_FILE", COOKIE_FILE)
    if os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
            
    return opts

def download_media(url: str, base_url: str) -> list[str]:
    downloaded_urls = []
    ydl_opts = get_ydl_options()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False, process=False)
            if not info:
                raise HTTPException(status_code=400, detail="Unable to extract media from the provided URL.")
            
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
                    ext = entry.get('ext', 'mp4')
                    filename = f"{entry_id}_{idx}.{ext}"
                    full_path = os.path.join(DOWNLOADS_DIR, filename)
                    if not os.path.exists(full_path):
                        alt_filename = f"{entry_id}_1.{ext}"
                        alt_path = os.path.join(DOWNLOADS_DIR, alt_filename)
                        if os.path.exists(alt_path):
                            filename = alt_filename
                        else:
                            matched = [f for f in os.listdir(DOWNLOADS_DIR) if f.startswith(entry_id)]
                            if matched:
                                filename = matched[0]
                    downloaded_urls.append(f"{base_url}/files/{filename}")
                elif entry.get('thumbnails'):
                    thumbnails = entry['thumbnails']
                    best_thumbnail = thumbnails[-1]['url']
                    filename = f"{entry_id}_{idx}.jpg"
                    full_path = os.path.join(DOWNLOADS_DIR, filename)
                    
                    req = urllib.request.Request(
                        best_thumbnail,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    with urllib.request.urlopen(req) as response, open(full_path, 'wb') as out_file:
                        out_file.write(response.read())
                    downloaded_urls.append(f"{base_url}/files/{filename}")
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Download error: {str(e)}")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal extraction error: {str(e)}")

    return downloaded_urls

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Instagram Downloader API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "download": "POST /download",
            "delete": "POST /delete",
            "files": "GET /files/{filename}"
        }
    }

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/health")
def health_check():
    return {"status": "online", "message": "Instagram Downloader API is active"}

@app.post("/download")
def download_endpoint(payload: DownloadRequest, request: Request):
    print(f"📥 [REQUEST] Received download query for: {payload.url}", flush=True)
    try:
        # Construct base URL from environment variable if set, otherwise from request headers
        custom_base = os.environ.get("API_BASE_URL", "").rstrip('/')
        base_url = custom_base if custom_base else str(request.base_url).rstrip('/')
        urls = download_media(payload.url, base_url)
        if not urls:
            print(f"⚠️  [NOT FOUND] No downloadable media for: {payload.url}", flush=True)
            raise HTTPException(status_code=404, detail="No downloadable media found.")
        print(f"✅ [SUCCESS] Extracted {len(urls)} file(s): {urls}", flush=True)
        return {"status": "success", "download_urls": urls}
    except Exception as e:
        print(f"❌ [ERROR] Processing failed for {payload.url}: {e}", flush=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete")
def delete_endpoint(payload: DeleteRequest):
    input_str = payload.file_url.strip()
    print(f"🗑️  [DELETE] Request to delete: {input_str}", flush=True)
    
    # Extract filename from URL (e.g. https://.../files/DcjIV1-K8e8_1.mp4 -> DcjIV1-K8e8_1.mp4)
    if "/files/" in input_str:
        filename = input_str.split("/files/")[-1]
    else:
        filename = os.path.basename(input_str)
        
    target_path = os.path.abspath(os.path.join(DOWNLOADS_DIR, filename))
    
    if not target_path.startswith(DOWNLOADS_DIR):
        raise HTTPException(status_code=400, detail="Access denied. File must be within the downloads directory.")
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File not found.")
    
    try:
        os.remove(target_path)
        print(f"✅ [DELETED] File '{filename}' removed.", flush=True)
        return {"status": "success", "message": f"File '{filename}' deleted successfully."}
    except Exception as e:
        print(f"❌ [DELETE ERROR] Failed to delete file: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port, proxy_headers=True, forwarded_allow_ips="*")
