from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, DELETE_COMMANDS_AFTER
from drive_utils import upload_to_drive, get_random_file
import requests
import time

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def handle_telegram_update(data):
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    user_id = message.get("from", {}).get("id")

    if not chat_id or not text:
        return {"ok": True}

    if text.startswith("/start"):
        send_message(chat_id, "👋 Welcome! Send /images /videos /audio /document or /list /get <code>")
    elif text.startswith("/images"):
        send_temp_file(chat_id, "image", user_id)
    elif text.startswith("/videos"):
        send_temp_file(chat_id, "video", user_id)
    elif text.startswith("/get"):
        code = text.split(" ", 1)[-1].strip()
        send_secret_file(chat_id, code)
    elif text.startswith("/add") and user_id in ADMIN_USER_IDS:
        send_message(chat_id, "📥 Ready to receive files. Send now.")
    else:
        send_message(chat_id, "❓ Unknown command.")

    # Schedule deletion
    time.sleep(DELETE_COMMANDS_AFTER)
    delete_message(chat_id, message["message_id"])

    return {"ok": True}

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def delete_message(chat_id, message_id):
    requests.post(f"{API_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

def send_temp_file(chat_id, category, user_id):
    file_info = get_random_file(category)
    if not file_info:
        send_message(chat_id, f"No {category} files available.")
        return
    file_id = file_info["file_id"]
    requests.post(f"{API_URL}/sendDocument", json={"chat_id": chat_id, "document": file_id})
    time.sleep(900)
    requests.post(f"{API_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": file_id})

def send_secret_file(chat_id, code):
    # Lookup logic for secret file based on code
    send_message(chat_id, f"Requested file with code: {code}")
