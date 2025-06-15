from fastapi import Request
import requests
import os
from downloader import download_all_assets

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def telegram_webhook(request: Request):
    data = await request.json()
    print("Received Telegram update:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    if text == "/start":
        send_message(chat_id, "👋 Hi! I'm alive and ready to download. Just send me a video link.")
    elif text.startswith("http"):
        send_message(chat_id, "⏬ Downloading your video in ultra HD...")

        meta = download_all_assets(text)

        if not meta:
            send_message(chat_id, "❌ Failed to download video. Please check the link.")
        else:
            video_path = f"./static/videos/{os.path.basename(meta['url'])}"
            file_size = os.path.getsize(video_path)

            if file_size < 49 * 1024 * 1024:  # <49MB send as file
                send_video(chat_id, video_path)
            else:
                send_message(chat_id, f"✅ {meta['title']}\n📎 [Download Video]({meta['url']})", parse_mode="Markdown")
    else:
        send_message(chat_id, "❓ I didn't understand that. Send a video link or /start.")

    return {"ok": True}

def send_message(chat_id, text, parse_mode=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def send_video(chat_id, video_path):
    with open(video_path, "rb") as video:
        requests.post(
            f"{TELEGRAM_API}/sendVideo",
            data={"chat_id": chat_id},
            files={"video": video}
        )
