import yt_dlp
import os
import uuid

DOWNLOAD_DIR = "static/videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_all_assets(url: str):
    video_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo[height<=4320]+bestaudio/best/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        # Optional: for private videos with browser cookies
        # 'cookiesfrombrowser': ('chrome',),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_filename = os.path.basename(filename).rsplit('.', 1)[0] + ".mp4"
            filepath = os.path.join(DOWNLOAD_DIR, base_filename)

            return {
                "title": info.get("title", "Untitled Video"),
                "url": f"/static/videos/{base_filename}",
                "filepath": filepath,
                "short": os.path.getsize(filepath) < 45 * 1024 * 1024  # Under 45MB
            }

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None
