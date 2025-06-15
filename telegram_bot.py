from fastapi import Request
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def telegram_webhook(request: Request):
    data = await request.json()
    print("📩 Telegram update received:", data)

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        print("⚠️ No chat_id found in message")
        return {"ok": False, "error": "No chat_id"}

    if text == "/start":
        send_message(chat_id, "👋 Hi! I'm alive and ready to download.")
    else:
        send_message(chat_id, "❓ I didn't understand that. Send /start to begin.")

    return {"ok": True}

def send_message(chat_id, text):
    response = requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })
    if response.status_code != 200:
        print("❌ Failed to send message:", response.text)
