import os
import re
import logging
import tempfile
from typing import Dict
from urllib.parse import urlparse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from config import MAX_FILE_SIZE_MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_PATTERNS = {
    'youtube': r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+',
    'instagram': r'(https?://)?(www\.)?instagram\.com/(reel|p|tv)/.+',
    # Add more patterns as needed
}

def is_valid_url(url: str) -> bool:
    """Check if the URL matches any of the supported platforms."""
    for pattern in URL_PATTERNS.values():
        if re.match(pattern, url):
            return True
    return False

def download_media(url: str, format_type: str, temp_dir: str) -> Dict:
    """Download media from the given URL."""
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best' if format_type == 'video' else 'bestaudio[ext=m4a]',
        'restrictfilenames': True,
        'noplaylist': True,
        'max_filesize': MAX_FILE_SIZE_MB * 1024 * 1024,  # Convert MB to bytes
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            return {
                'file_path': file_path,
                'title': info.get('title'),
            }
    except DownloadError as e:
        logger.error(f"Download failed: {e}")
        return {'error': str(e)}
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {'error': str(e)}
