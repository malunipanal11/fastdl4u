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
        'format': 'bestvideo+bestaudio/best',  # Gets best quality
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        # Convert to .mp4 if needed
        base_filename = os.path.basename(filename).rsplit('.', 1)[0] + ".mp4"
        file_path = os.path.join(DOWNLOAD_DIR, base_filename)

        return {
            "title": info.get("title", "Unknown Title"),
            "filename": base_filename,
            "path": file_path,
            "url": f"/static/videos/{base_filename}"
        }
