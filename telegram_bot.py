from fastapi import Request
import requests
import os
from downloader import download_all_assets

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_video(chat_id, filepath, caption=""):
    with open(filepath, 'rb') as f:
        requests.post(f"{TELEGRAM_API}/sendVideo", data={
            "chat_id": chat_id,
            "caption": caption
        }, files={"video": f})

async def telegram_webhook(request: Request):
    data = await request.json()
    print("📩 Telegram update:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return {"ok": True}

    if text == "/start":
        send_message(chat_id, "👋 Hi! I'm alive and ready to download. Just send me a video link.")
        return {"ok": True}

    # Assume it’s a URL
    send_message(chat_id, "⏬ Downloading your video in ultra HD...")

    result = download_all_assets(text)
    if not result:
        send_message(chat_id, "❌ Failed to download video. Please check the link.")
        return {"ok": True}

    if result["short"]:
        send_video(chat_id, result["filepath"], caption=f"✅ {result['title']}")
    else:
        public_url = f"https://fastdl4u.onrender.com{result['url']}"
        send_message(chat_id, f"✅ {result['title']}\n\n📎 File too large for Telegram. [Click to Download]({public_url})")
    
    return {"ok": True}
