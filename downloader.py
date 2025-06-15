from yt_dlp import YoutubeDL
import os

def download_all_assets(url: str, output_dir='static/videos'):
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'writethumbnail': True,
        'writeinfojson': True,
        'quiet': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    full_download_opts = {
        **ydl_opts,
        'format': 'bestvideo[height>=1080]+bestaudio/best',
    }

    with YoutubeDL(full_download_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_file = ydl.prepare_filename(info)
        audio_file = video_file.rsplit('.', 1)[0] + '.mp3'
        thumbnail_url = info.get('thumbnail', '')
        thumbnail_name = thumbnail_url.split("/")[-1]
        thumbnail_file = os.path.join(output_dir, thumbnail_name)

        metadata = {
            'title': info.get('title'),
            'duration': info.get('duration'),
            'size': info.get('filesize_approx', 0),
            'quality': info.get('format'),
            'platform': info.get('extractor_key'),
            'video_file': video_file,
            'audio_file': audio_file,
            'thumbnail': f"/static/videos/{thumbnail_name}"
        }

        return metadata
