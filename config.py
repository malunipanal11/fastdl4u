import os

# Telegram Bot Token (required)
TOKEN = os.getenv("BOT_TOKEN", "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw")

# Admin User IDs (comma-separated string in env, parsed to list of ints)
ADMIN_IDS = [int(uid.strip()) for uid in os.getenv("ADMIN_IDS", "5558589142").split(",") if uid.strip().isdigit()]

# GoFile API Token (required for uploads)
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN", "7MaibQTxRi8BN0zKD8NDoCwXDABdA8Jq")

# Webhook URL (Render uses this for receiving updates)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://fastdl4u.onrender.com/webhook")

# Expiry times for auto-deleting messages (per content type)
EXPIRE_COMMANDS = {
    "image": 600,
    "video": 900,
    "audio": 900,
    "code": 600,
}
