import os

# Telegram Bot Token
TOKEN = os.getenv("BOT_TOKEN", "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw")

# List of admin user IDs (must be integers)
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "5558589142").split(",")]

# GoFile API Token
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN", "7MaibQTxRi8BN0zKD8NDoCwXDABdA8Jq")

# Webhook URL
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://fastdl4u.onrender.com/webhook")

# Optional: Default expiry commands per category (in seconds)
EXPIRE_COMMANDS = {
    "image": 600,
    "video": 900,
    "audio": 900,
    "code": 600
}
