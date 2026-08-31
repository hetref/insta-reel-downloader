import os
import urllib.request
import yt_dlp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="Instagram Downloader API")

DOWNLOADS_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str

class DeleteRequest(BaseModel):
    file_path: str

YDL_OPTS = {
    'format': 'best',
    'outtmpl': os.path.join(DOWNLOADS_DIR, '%(id)s_%(playlist_index|1)s.%(ext)s'),
    'cookiesfrombrowser': ('chrome',),
    'ignoreerrors': True,
    'quiet': True,
}

def download_media(url: str) -> list[str]:
    downloaded_files = []
    
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
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
                # Let yt-dlp download video
                ydl.process_ie_result(entry, download=True)
                ext = entry.get('ext', 'mp4')
                filename = f"{entry_id}_{idx}.{ext}"
                full_path = os.path.join(DOWNLOADS_DIR, filename)
                # Fallback check if playlist index default was used
                if not os.path.exists(full_path):
                    alt_path = os.path.join(DOWNLOADS_DIR, f"{entry_id}_1.{ext}")
                    if os.path.exists(alt_path):
                        full_path = alt_path
                downloaded_files.append(os.path.relpath(full_path, start=os.getcwd()))
            elif entry.get('thumbnails'):
                # Download high-res thumbnail image directly
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
                downloaded_files.append(os.path.relpath(full_path, start=os.getcwd()))

    return downloaded_files

@app.post("/download")
def download_endpoint(payload: DownloadRequest):
    try:
        files = download_media(payload.url)
        if not files:
            raise HTTPException(status_code=404, detail="No downloadable media found.")
        return {"status": "success", "downloaded_files": files}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete")
def delete_endpoint(payload: DeleteRequest):
    target_path = os.path.abspath(payload.file_path)
    
    # Security check: Ensure file resides inside the allowed DOWNLOADS_DIR
    if not target_path.startswith(DOWNLOADS_DIR):
        raise HTTPException(status_code=400, detail="Access denied. File must be within the downloads directory.")
    
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File not found.")
    
    try:
        os.remove(target_path)
        return {"status": "success", "message": f"File '{payload.file_path}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
