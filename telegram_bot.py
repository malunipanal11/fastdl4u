from fastapi import Request
import requests
import os
from downloader import download_all_assets  # Ensure this function returns metadata with filename/path

BOT_TOKEN = os.getenv("BOT_TOKEN", "7302709681:AAH-T7pWa89wVA3IjHiufFge7Vc4q86Mhx8")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
BASE_URL = os.getenv("BASE_URL", "https://fastdl4u.onrender.com")

async def telegram_webhook(request: Request):
    data = await request.json()
    print("Received Telegram update:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    if text == "/start":
        send_message(chat_id, "👋 Hi! I'm alive and ready to download.")
    elif "instagram.com" in text:
        try:
            meta = download_all_assets(text)
            video_url = f"{BASE_URL}/static/videos/{meta['filename']}"
            send_message(chat_id, f"✅ Download complete!\n🎬 Video: {video_url}")
        except Exception as e:
            print("Error downloading:", e)
            send_message(chat_id, "⚠️ Failed to download. Please try again later.")
    else:
        send_message(chat_id, "❓ I didn't understand that. Send a valid Instagram reel/video link.")

    return {"ok": True}

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })
