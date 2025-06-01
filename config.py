import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "8186227901:AAH9MU07NdnAUFiywAIMpxHitA5V3O1b3hw")

# Admin User IDs
ADMIN_IDS = [int(uid.strip()) for uid in os.getenv("ADMIN_IDS", "5558589142").split(",") if uid.strip().isdigit()]

# GoFile API Token
GOFILE_TOKEN = os.getenv("GOFILE_TOKEN", "7MaibQTxRi8BN0zKD8NDoCwXDABdA8Jq")

# Webhook URL
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN", "https://fastdl4u.onrender.com")

# Message expiration settings
EXPIRE_COMMANDS = {
    "image": 600,
    "video": 900,
    "audio": 900,
    "code": 600,
}
