import os

# Telegram Bot Token (required)
BOT_TOKEN = os.getenv("BOT_TOKEN", "your-bot-token")

# Webhook URL (Render uses this for receiving updates)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com/webhook")

# GoFile API Token (for real uploads, optional here)
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN", "your-gofile-token")

# Admin User IDs (comma-separated string in env, parsed to list of ints)
ADMIN_IDS = [int(uid.strip()) for uid in os.getenv("ADMIN_IDS", "123456789").split(",") if uid.strip().isdigit()]

# Expiry times for auto-deleting messages (per content type)
EXPIRE_COMMANDS = {
    "image": 600,
    "video": 900,
    "audio": 900,
    "code": 600,
}
