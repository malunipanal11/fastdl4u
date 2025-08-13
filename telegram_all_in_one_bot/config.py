import os
from dotenv import load_dotenv

# Load environment variables from .env (for local testing)
load_dotenv()

API_ID = int(os.getenv("API_ID"))        # Telegram API ID
API_HASH = os.getenv("API_HASH")         # Telegram API Hash
BOT_TOKEN = os.getenv("BOT_TOKEN")       # Bot Token from @BotFather
