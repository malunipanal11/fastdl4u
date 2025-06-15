import yt_dlp
import os
import uuid

DOWNLOAD_DIR = "static/videos"
MAX_FILE_SIZE_MB = 50  # Telegram max file upload ~50MB for bots

def download_all_assets(url: str):
    video_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'writesubtitles': False,
        'writeautomaticsub': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            final_path = os.path.splitext(filename)[0] + ".mp4"

            if not os.path.exists(final_path):
                return None

            file_size_mb = os.path.getsize(final_path) / (1024 * 1024)
            short = file_size_mb <= MAX_FILE_SIZE_MB

            return {
                "title": info.get("title", "Untitled"),
                "url": f"/static/videos/{os.path.basename(final_path)}",
                "filepath": final_path,
                "short": short,
                "size_mb": round(file_size_mb, 2)
            }

    except Exception as e:
        print("❌ Download error:", e)
        return None
