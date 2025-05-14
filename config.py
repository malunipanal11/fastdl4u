import os
import logging

logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))  # Default to 0 if not provided
API_HASH = os.getenv("API_HASH")

# Check if all required environment variables are provided
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN environment variable is not set. The bot will not function correctly.")

MAX_FILE_SIZE_MB = 150

WELCOME_MESSAGE = """
👋 Welcome to FastDL4U Bot!

I can help you download videos and audio from various platforms:
- YouTube
- Instagram
- TikTok
- Threads
- And many more!

Simply send me a link, and I'll handle the rest.
"""

HELP_MESSAGE = """
📝 *How to use FastDL4U Bot:*

1. Send any video URL from YouTube, Instagram, TikTok, etc.
2. Choose to download as video or audio (MP3)
3. Wait for the download and enjoy!

*Commands:*
/start - Start the bot
/help - Show this help message
/cleanup - Remove old downloads and message history
"""
