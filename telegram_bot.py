from fastapi import Request
import requests
import os
from downloader import download_all_assets

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Helpers
def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_video(chat_id, video_path, caption="Here's your video 🎥"):
    with open(video_path, "rb") as video_file:
        requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={"chat_id": chat_id, "caption": caption},
            files={"video": video_file}
        )

# Main Webhook
async def telegram_webhook(request: Request):
    data = await request.json()
    print("Received Telegram update:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": False}

    if text.startswith("/start"):
        send_message(chat_id, "👋 Hi! I'm alive and ready to download. Just send me a video link.")
        return {"ok": True}

    if any(site in text for site in ["instagram.com", "youtube.com", "tiktok.com", "facebook.com"]):
        send_message(chat_id, "⏬ Downloading your video in ultra HD...")
        try:
            meta = download_all_assets(text)
            video_path = meta["path"]

            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

            if file_size_mb <= 50:
                send_video(chat_id, video_path, caption=f"✅ {meta['title']}")
            else:
                full_url = f"https://fastdl4u.onrender.com{meta['url']}"
                send_message(chat_id, f"📁 Your video is too large to send here.\n🔗 Download it from: {full_url}")

        except Exception as e:
            print("Download failed:", e)
            send_message(chat_id, "❌ Failed to download video. Please check the link.")
        return {"ok": True}

    send_message(chat_id, "❓ I didn't understand that. Send a valid video link or /start.")
    return {"ok": True}
