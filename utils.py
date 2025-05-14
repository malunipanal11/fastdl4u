import os
import shutil
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def format_size(size_bytes: int) -> str:
    """Format size in bytes to a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def create_temp_dir(user_id: int, base_dir: str) -> str:
    """Create a temporary directory for user downloads."""
    user_dir = os.path.join(base_dir, str(user_id))
    
    # Create directory if it doesn't exist
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    
    return user_dir

def cleanup_user_data(user_id: int, user_data: Dict[int, Any], temp_dir: str) -> None:
    """Clean up user data and downloaded files."""
    # Clean up downloaded files
    user_dir = os.path.join(temp_dir, str(user_id))
    if os.path.exists(user_dir):
        try:
            shutil.rmtree(user_dir)
            logger.info(f"Cleaned up directory for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to clean up directory for user {user_id}: {e}")
    
    # Clean up user data
    if user_id in user_data:
        user_data.pop(user_id)
        logger.info(f"Cleaned up data for user {user_id}")
