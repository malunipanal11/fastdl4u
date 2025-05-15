import os
from yt_dlp import YoutubeDL
import re
import asyncio
import logging
from urllib.parse import urlparse
import tempfile
from typing import Dict, Optional, Union, Any

import yt_dlp
from yt_dlp.utils import DownloadError

from config import MAX_FILE_SIZE_MB

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# URL patterns for different platforms
URL_PATTERNS = {
    'youtube': r'(youtube\.com|youtu\.be)',
    'instagram': r'(instagram\.com|instagr\.am)',
    'tiktok': r'(tiktok\.com|vm\.tiktok\.com)',
    'threads': r'threads\.net',
    'twitter': r'(twitter\.com|x\.com)',
    'facebook': r'(facebook\.com|fb\.watch)',
}

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid and from a supported platform."""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        
        # Check if the URL is from a supported platform
        domain = result.netloc.lower()
        for pattern in URL_PATTERNS.values():
            if re.search(pattern, domain):
                return True
        
        return False
    except Exception:
        return False

def get_platform_name(url: str) -> str:
    """Determine platform name from URL."""
    domain = urlparse(url).netloc.lower()
    
    for platform, pattern in URL_PATTERNS.items():
        if re.search(pattern, domain):
            return platform.capitalize()
    
    return "Unknown"

def download_media(url, format_type, download_path):
    print("Downloading from:", url)

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    ydl_opts = {
        'format': 'best' if format_type == 'video' else 'bestaudio',
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'quiet': False,
        'noplaylist': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        print("Download successful:", file_path)
        return {
            'file_path': file_path,
            'title': info.get('title', 'Downloaded Media')
        }

    except Exception as e:
        print("Download failed with error:", str(e))
        return {'error': str(e)}
    """
    Download media from the provided URL.
    
    Args:
        url: The URL to download from
        format_type: Either 'video' or 'audio'
        output_dir: Directory to save the downloaded file
    
    Returns:
        Dict containing file_path and other info, or error message
    """
    # Create a temporary file to store output
    temp_name = next(tempfile._get_candidate_names())
    max_filesize = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, f'{temp_name}.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': True,
        'filesize_limit': max_filesize,
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
    else:  # video
        ydl_opts.update({
            'format': 'best[filesize<{}]/bestvideo[filesize<{}]+bestaudio/best'.format(
                max_filesize, max_filesize
            ),
        })
    
    try:
        # Create an executor for running yt-dlp in a separate thread
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        
        # Execute the download
        info_dict = await loop.run_in_executor(None, download)
        
        if not info_dict:
            return {'error': 'Could not download the media'}
        
        # Get the downloaded file path
        if 'entries' in info_dict:
            # Playlist, get the first video
            info = info_dict['entries'][0]
        else:
            # Single video
            info = info_dict
        
        # Determine the file extension and path
        if format_type == 'audio':
            ext = 'mp3'
        else:
            ext = info.get('ext', 'mp4')
        
        file_path = os.path.join(output_dir, f'{temp_name}.{ext}')
        
        # Check if file exists and has a valid size
        if not os.path.exists(file_path):
            all_files = os.listdir(output_dir)
            for file in all_files:
                if file.startswith(temp_name):
                    file_path = os.path.join(output_dir, file)
                    break
        
        # If we still can't find the file, return error
        if not os.path.exists(file_path):
            return {'error': 'Downloaded file not found'}
        
        # Check the file size
        file_size = os.path.getsize(file_path)
        if file_size > max_filesize:
            os.remove(file_path)
            return {'error': f'File size exceeds the limit of {MAX_FILE_SIZE_MB}MB'}
        
        # Prepare the result
        result = {
            'file_path': file_path,
            'title': info.get('title', 'Downloaded Media'),
            'uploader': info.get('uploader', 'Unknown'),
            'duration': info.get('duration', 0),
            'platform': get_platform_name(url),
        }
        
        return result
    
    except DownloadError as e:
        logger.error(f"Download error: {str(e)}")
        return {'error': f'Download error: {str(e)}'}
    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}")
        return {'error': f'Error: {str(e)}'}
