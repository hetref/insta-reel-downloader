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
                
                # Check if it has video formats
                has_video = False
                if entry.get('formats'):
                    has_video = any(f.get('vcodec') != 'none' for f in entry['formats'])
                
                entry_id = entry.get('id', f'item_{idx}')
                
                if has_video:
                    print(f"[Video] Downloading video content for {entry_id}...")
                    ydl.process_ie_result(entry, download=True)
                elif entry.get('thumbnails'):
                    thumbnails = entry['thumbnails']
                    best_thumbnail = thumbnails[-1]['url']
                    file_path = os.path.join("downloads", f"{entry_id}_{idx}.jpg")
                    print(f"[Image] Downloading image content to {file_path}...")
                    
                    req = urllib.request.Request(
                        best_thumbnail,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
                        out_file.write(response.read())
                    print(f"[Image] Saved: {file_path}")

if __name__ == "__main__":
    try:
        download_instagram_media(TEST_URLS, ydl_opts)
    except Exception as e:
        print(f"Extraction failed with error: {e}")
        exit(1)
