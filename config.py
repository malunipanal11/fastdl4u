import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# Gofile API
GOFILE_API = "https://api.gofile.io"
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")

# File Paths (for categorization)
CATEGORIES = {
    "images": "Images",
    "videos": "Videos",
    "audios": "Audio",
    "secret": "Secret",
}

# Expiry durations (in seconds)
EXPIRE_COMMANDS = {
    "img": 300,   # 5 min
    "vid": 600,   # 10 min
    "aud": 600,   # 10 min
    "code": 30    # /get code or command expiration
}
