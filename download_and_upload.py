import yt_dlp
import requests
import os

def download_video(link, audio_only=False):
    ydl_opts = {
        'format': 'bestaudio/best' if audio_only else 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=True)
        file_path = ydl.prepare_filename(info)

    return {
        'title': info.get('title'),
        'duration': info.get('duration'),
        'file_path': file_path,
        'thumbnail': info.get('thumbnail'),
        'ext': info.get('ext'),
        'filesize': info.get('filesize', 0),
        'webpage_url': info.get('webpage_url'),
    }

def upload_to_fileio(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post('https://file.io/?expires=1d', files={'file': f})
        return response.json().get('link')