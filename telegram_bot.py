from fastapi import Request
import requests
import os
from downloader import download_all_assets

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_video_file(chat_id, filepath):
    with open(filepath, "rb") as video:
        requests.post(f"{TELEGRAM_API}/sendVideo", data={"chat_id": chat_id}, files={"video": video})

async def telegram_webhook(request: Request):
    data = await request.json()
    print("📩 Telegram update:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    if text == "/start":
        send_message(chat_id, "👋 Hi! I'm alive and ready to download. Just send me a video link.")
        return {"ok": True}

    if text.startswith("http"):
        send_message(chat_id, "⏬ Downloading your video in ultra HD...")

        meta = download_all_assets(text)
        if not meta:
            send_message(chat_id, "❌ Failed to download video. Please check the link.")
            return {"ok": True}

        title = meta["title"]
        filepath = meta["filepath"]
        url = meta["url"]

        if meta["short"]:
            send_video_file(chat_id, filepath)
        else:
            send_message(chat_id, f"✅ {title}\n\n📎 Download link:\nhttps://fastdl4u.onrender.com{url}")

        return {"ok": True}

    send_message(chat_id, "❓ I didn't understand that. Send /start or a valid video link.")
    return {"ok": True}
