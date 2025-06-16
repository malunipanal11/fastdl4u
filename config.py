import os

# Read values from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_IDS = list(map(int, os.getenv("ADMIN_USER_IDS", "").split(",")))
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "service_account.json")

DELETE_COMMANDS_AFTER = int(os.getenv("DELETE_COMMANDS_AFTER", "30"))  # seconds
DELETE_FILES_AFTER = int(os.getenv("DELETE_FILES_AFTER", "900"))       # seconds (15 min)
