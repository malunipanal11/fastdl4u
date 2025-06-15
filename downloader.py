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
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_filename = os.path.basename(filename).rsplit('.', 1)[0] + ".mp4"
            filepath = os.path.join(DOWNLOAD_DIR, base_filename)

            size_mb = os.path.getsize(filepath) / (1024 * 1024)

            return {
                "title": info.get("title", "Untitled"),
                "url": f"/static/videos/{base_filename}",
                "filepath": filepath,
                "size_mb": round(size_mb, 2),
                "short": size_mb <= 49  # only send file if small enough
            }

    except Exception as e:
        print("❌ Error downloading:", str(e))
        return None
