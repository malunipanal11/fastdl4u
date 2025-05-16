import os
import re
import logging
import tempfile
from typing import Dict
from urllib.parse import urlparse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from config import MAX_FILE_SIZE_MB

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

URL_PATTERNS = {
    'youtube': r'(youtube\.com|youtu\.be)',
    'instagram': r'(instagram\.com|instagr\.am)',
    'tiktok': r'(tiktok\.com|vm\.tiktok\.com)',
    'threads': r'threads\.net',
    'twitter': r'(twitter\.com|x\.com)',
    'facebook': r'(facebook\.com|fb\.watch)',
}

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        domain = result.netloc.lower()
        return any(re.search(p, domain) for p in URL_PATTERNS.values())
    except Exception:
        return False

def get_platform_name(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    for platform, pattern in URL_PATTERNS.items():
        if re.search(pattern, domain):
            return platform.capitalize()
    return "Unknown"

def download_media(url: str, format_type: str, output_dir: str) -> Dict:
    print(">>> Starting download from:", url)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    temp_name = next(tempfile._get_candidate_names())
    max_filesize = MAX_FILE_SIZE_MB * 1024 * 1024

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, f'{temp_name}.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
        'ignoreerrors': False,
        'filesize_limit': max_filesize,
        'ffmpeg_location': '/usr/bin/ffmpeg',  # Optional: set if you have ffmpeg path issues
    }

    if format_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': f'best[filesize<{max_filesize}]',
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            return {'error': 'Could not extract media info'}

        # Handle playlists
        if 'entries' in info:
            info = info['entries'][0]

        ext = 'mp3' if format_type == 'audio' else info.get('ext', 'mp4')
        file_path = os.path.join(output_dir, f'{temp_name}.{ext}')

        # Check fallback in case yt-dlp changed the filename
        if not os.path.exists(file_path):
            for file in os.listdir(output_dir):
                if file.startswith(temp_name):
                    file_path = os.path.join(output_dir, file)
                    break

        if not os.path.exists(file_path):
            return {'error': 'Downloaded file not found'}

        if os.path.getsize(file_path) > max_filesize:
            os.remove(file_path)
            return {'error': f'File size exceeds the limit of {MAX_FILE_SIZE_MB}MB'}

        return {
            'file_path': file_path,
            'title': info.get('title', 'Downloaded Media'),
            'uploader': info.get('uploader', 'Unknown'),
            'duration': info.get('duration', 0),
            'platform': get_platform_name(url),
        }

    except DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        return {'error': f'Download error: {str(e)}'}
    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return {'error': f'Error: {str(e)}'}
