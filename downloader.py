import yt_dlp
import os
import uuid

DOWNLOAD_DIR = "static/videos"

def download_all_assets(url: str):
    video_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base_filename = os.path.basename(filename).rsplit('.', 1)[0] + ".mp4"

        return {
            "title": info.get("title", "Unknown Title"),
            "url": f"/static/videos/{base_filename}"
        }
