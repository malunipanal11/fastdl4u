import os
import json
import logging
import requests
import asyncio
from flask import Flask, request, jsonify, render_template
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# === ENV Configuration ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
log_file = "file_log.json"

# === Flask App ===
app = Flask(__name__)
telegram_app: Application = Application.builder().token(TELEGRAM_TOKEN).build()

# === Helper Functions ===
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
    # Simulated file details (replace with actual yt-dlp if needed)
    return {
        "title": "Sample Video",
        "thumbnail": "https://via.placeholder.com/400x200.png?text=Thumbnail",
        "duration": "123",
        "size": "5.4 MB",
        "quality": "720p",
        "file_url": "https://file.io/example",
        "file_name": "video.mp4"
    }

# === Telegram Bot Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a social media link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    await update.message.reply_text("⏳ Processing your link...")

    result = fake_download(link, "video")
    try:
        # Download file temporarily
        file_data = requests.get(result["file_url"])
        with open(result["file_name"], "wb") as f:
            f.write(file_data.content)

        # Send the video
        with open(result["file_name"], "rb") as f:
            await update.message.reply_video(
                video=f,
                caption=f"🎬 {result['title']} ({result['quality']}, {result['size']})"
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

    save_to_log(result)

# === Register Handlers ===
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

# === Flask Routes ===
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

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.create_task(telegram_app.process_update(update))
    return "ok"

# === Webhook Setup ===
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    full_url = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
    res = requests.post(url, json={"url": full_url})
    print("🔗 Webhook response:", res.json())

# === Main Entrypoint ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
