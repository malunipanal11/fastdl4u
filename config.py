import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram Bot Settings ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set in the .env file")

# Admin Telegram user IDs, comma-separated in .env
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
if not ADMIN_IDS:
    print("⚠️ Warning: No ADMIN_IDS configured")

# --- Gofile API Settings ---
GOFILE_API = "https://api.gofile.io"
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN")
if not GOFILE_TOKEN:
    print("⚠️ Warning: GOFILE_TOKEN is not set. Uploads may fail.")

# --- File Category Mappings ---
CATEGORIES = {
    "images": "Images",
    "videos": "Videos",
    "audios": "Audio",
    "secret": "Secret",
}

# --- Command Expiration Timers (in seconds) ---
EXPIRE_COMMANDS = {
    "img": 300,   # 5 minutes
    "vid": 600,   # 10 minutes
    "aud": 600,   # 10 minutes
    "code": 30    # Used in /get <code> auto-delete
}
