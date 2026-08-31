import os
import urllib.request
import yt_dlp
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(
    title="Instagram Downloader API",
    description="API to download Instagram Reels, Posts, and Carousels and manage files locally."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

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
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    if os.path.exists(COOKIE_FILE):
        opts['cookiefile'] = COOKIE_FILE
    else:
        try:
            opts['cookiesfrombrowser'] = ('chrome',)
        except Exception:
            pass
            
    return opts

def download_media(url: str, base_url: str) -> list[str]:
    downloaded_urls = []
    ydl_opts = get_ydl_options()
    
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
                downloaded_urls.append(f"{base_url}/files/{filename}")
            elif entry.get('thumbnails'):
                thumbnails = entry['thumbnails']
                best_thumbnail = thumbnails[-1]['url']
                filename = f"{entry_id}_{idx}.jpg"
                full_path = os.path.join(DOWNLOADS_DIR, filename)
                
                req = urllib.request.Request(
                    best_thumbnail,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req) as response, open(full_path, 'wb') as out_file:
                    out_file.write(response.read())
                downloaded_urls.append(f"{base_url}/files/{filename}")

    return downloaded_urls

@app.get("/health")
def health_check():
    return {"status": "online", "message": "Instagram Downloader API is active"}

@app.post("/download")
def download_endpoint(payload: DownloadRequest, request: Request):
    try:
        # Dynamically construct base URL (e.g. https://reel-downloader-api.aryanshinde.in)
        base_url = str(request.base_url).rstrip('/')
        urls = download_media(payload.url, base_url)
        if not urls:
            raise HTTPException(status_code=404, detail="No downloadable media found.")
        return {"status": "success", "download_urls": urls}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete")
def delete_endpoint(payload: DeleteRequest):
    input_str = payload.file_url.strip()
    
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
        return {"status": "success", "message": f"File '{filename}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
