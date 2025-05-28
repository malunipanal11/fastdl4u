import os
import json
import threading
import asyncio
import logging
from flask import Flask, request, jsonify, render_template, send_file
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import requests
from datetime import datetime

# == Setup ==
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://your-render-url.onrender.com")
LOG_FILE = "file_log.json"

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f:
        json.dump([], f)

# == Helper Functions ==
def save_to_log(file_data):
    with open(LOG_FILE, 'r+') as f:
        data = json.load(f)
        data.insert(0, file_data)
        f.seek(0)
        json.dump(data, f, indent=2)

def download_media(url, format):
    ydl_opts = {
        'format': 'bestaudio/best' if format == 'audio' else 'best',
        'outtmpl': 'downloads/%(title).80s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3'
        }] if format == 'audio' else [],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return {
            'title': info.get('title'),
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
            'filename': filename,
            'ext': info.get('ext'),
            'url': url,
            'size': round(info.get('filesize', 0) / 1048576, 2),
            'quality': info.get('format'),
        }

def upload_to_fileio(filepath):
    with open(filepath, 'rb') as f:
        res = requests.post("https://file.io", files={"file": f})
    return res.json().get("link")

# == Flask Routes ==
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/file_log.json")
def file_log():
    return send_file(LOG_FILE)

@app.route("/api/process", methods=["POST"])
def process():
    try:
        data = request.get_json()
        url = data['link']
        fmt = data['format']
        info = download_media(url, fmt)
        file_url = upload_to_fileio(info['filename'])
        info['file_url'] = file_url
        save_to_log(info)
        return jsonify(info)
    except Exception as e:
        logging.error("Processing error", exc_info=True)
        return jsonify({'error': str(e)}), 500

# == Telegram Bot Logic ==
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a video/audio link and I'll download it for you!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat.id
    try:
        await update.message.reply_text("⏳ Processing your link...")

        info = download_media(url, 'video')
        with open(info['filename'], 'rb') as f:
            await context.bot.send_video(chat_id=chat_id, video=f, caption=info['title'])

        # Store and upload
        file_url = upload_to_fileio(info['filename'])
        info['file_url'] = file_url
        save_to_log(info)

    except Exception as e:
        logging.error("Telegram bot error", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def bot_main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("🤖 Bot started.")
    await application.run_polling()

# == Launch Telegram Bot in Thread ==
def run_bot():
    asyncio.run(bot_main())

threading.Thread(target=run_bot).start()

# == Start Flask ==
if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run(host="0.0.0.0", port=5000)