from fastapi import Request
import requests
import os
from downloader import download_all_assets

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SERVER_BASE_URL = os.getenv("SERVER_URL", "https://fastdl4u.onrender.com")  # Replace with your URL if needed

async def telegram_webhook(request: Request):
    data = await request.json()
    print("Received Telegram update:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return {"ok": True}

    if text == "/start":
        send_message(chat_id, "👋 Hi! I'm alive and ready to download. Just send me a video link.")
    elif "http" in text:
        send_message(chat_id, "⏬ Downloading your video in ultra HD...")
        meta = download_all_assets(text)

        if meta is None:
            send_message(chat_id, "❌ Failed to download video. Please check the link.")
        else:
            file_path = meta["path"]
            file_size = os.path.getsize(file_path)

            if file_size < 45 * 1024 * 1024:
                send_video_file(chat_id, file_path, caption=f"✅ {meta['title']}")
            else:
                video_url = f"{SERVER_BASE_URL}{meta['url']}"
                send_message(chat_id, f"✅ {meta['title']}\n📎 [Download Link]({video_url})", parse_mode="Markdown")
    else:
        send_message(chat_id, "❓ I didn't understand that. Send me a video link or type /start.")

    return {"ok": True}

def send_message(chat_id, text, parse_mode=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def send_video_file(chat_id, file_path, caption=""):
    with open(file_path, "rb") as video:
        requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={
                "chat_id": chat_id,
                "caption": caption
            },
            files={
                "video": video
            }
        )
