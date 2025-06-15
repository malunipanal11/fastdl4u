import yt_dlp
import os

DOWNLOAD_DIR = "static/videos"

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in " ._-").rstrip()

def download_all_assets(url: str) -> dict:
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "video")
        ext = info.get("ext", "mp4")
        filename = sanitize_filename(f"{title}.{ext}")
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        return {
            "title": title,
            "filepath": f"/static/videos/{filename}"
        }
