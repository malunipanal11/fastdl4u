import yt_dlp
import os
import uuid

DOWNLOAD_DIR = "static/videos"

def download_all_assets(url: str):
    video_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo[height<=4320]+bestaudio/best',  # up to 8K
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'cookiesfrombrowser': ('chrome',),  # if running locally with Chrome
        'default_search': 'ytsearch'  # fallback if it's a search query
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_filename = os.path.basename(filename).rsplit('.', 1)[0] + ".mp4"

            return {
                "title": info.get("title", "Unknown Title"),
                "url": f"/static/videos/{base_filename}",
                "filepath": f"static/videos/{base_filename}",
                "short": os.path.getsize(f"static/videos/{base_filename}") < 45 * 1024 * 1024  # under 45MB for Telegram
            }
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None
