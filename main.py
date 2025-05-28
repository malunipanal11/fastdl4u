import os
import json
import logging
import threading
import requests
from flask import Flask, request, jsonify, render_template
import telebot
from telebot.types import Update, InputFile

# === Secure Config ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)
log_file = "file_log.json"

# === Helpers ===
def save_to_log(data):
    try:
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(data)
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print("Log error:", e)

def fake_download(link, format):
    # Simulated download
    return {
        "title": "Sample Video",
        "thumbnail": "https://via.placeholder.com/400x200.png?text=Thumbnail",
        "duration": "123",
        "size": "5.4",
        "quality": "720p",
        "file_url": "https://file.io/example",
        "file_name": "video.mp4"
    }

# === Telegram Handlers ===
@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.send_message(message.chat.id, "👋 Send a social media link to download.")

@bot.message_handler(func=lambda m: True)
def handle_link(message):
    chat_id = message.chat.id
    link = message.text.strip()
    bot.send_message(chat_id, "⏳ Processing...")

    result = fake_download(link, "video")

    try:
        file_data = requests.get(result["file_url"])
        with open(result["file_name"], "wb") as f:
            f.write(file_data.content)

        with open(result["file_name"], "rb") as f:
            bot.send_video(chat_id, f, caption=f"🎬 {result['title']}")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error downloading file: {str(e)}")

    save_to_log(result)

# === Web App ===
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/api/process", methods=["POST"])
def process_api():
    data = request.get_json()
    link = data.get("link")
    format = data.get("format", "video")

    result = fake_download(link, format)
    save_to_log(result)
    return jsonify(result)

@app.route("/webhook/" + TELEGRAM_TOKEN, methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    bot.process_new_updates([update])
    return "ok"

# === Webhook Setup ===
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    full_url = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
    res = requests.post(url, json={"url": full_url})
    print("🔗 Webhook setup response:", res.json())

# === App Start ===
def start_bot():
    print("🤖 Bot started.")
    set_webhook()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=5000)
